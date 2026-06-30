"""check-canonical-doc-freshness.py unit tests.

PLAN-112-FOLLOWUP-canonical-doc-refresh-gate W5 / AC6 — covers the
release-time doc-freshness gate that closes F-D4.

Cases (W5): fresh / bootstrap (stamped at current VERSION) / N+1 behind by
tier fails / override pass-with-warning / malformed stamp fail-CLOSED /
absent stamp fail-CLOSED (distinct sub-case) / --json shape stable.
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-canonical-doc-freshness.py"

# Mirror DOC_TIERS in the script.
DOCS = {
    "SECURITY.md": 1, "VERSIONING.md": 1, "SBOM.md": 1,
    "README.md": 3, "INSTALL.md": 3, "SUPPORT.md": 3,
    ".claude/adr/README.md": 3,
}


def _run(root: Path, json_mode: bool = False, waiver: str | None = None):
    env = os.environ.copy()
    env.pop("CEO_DOC_FRESHNESS_WAIVER", None)
    if waiver is not None:
        env["CEO_DOC_FRESHNESS_WAIVER"] = waiver
    args = ["python3", str(SCRIPT), "--repo-root", str(root)]
    if json_mode:
        args.append("--json")
    return subprocess.run(args, capture_output=True, text=True, timeout=30, env=env)


def _scaffold(root: Path, version: str = "1.43.0", stamps: dict | None = None) -> None:
    """Write VERSION + all 7 docs. `stamps` overrides per-doc stamp text
    (value None => write a doc with NO stamp; key absent => stamp at VERSION)."""
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    stamps = stamps or {}
    for rel in DOCS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel in stamps:
            stamp = stamps[rel]
        else:
            stamp = f"<!-- last-reviewed: 2026-05-24 v{version} -->"
        body = f"# Title\n\n{stamp or ''}\n\nbody of {rel}\n"
        p.write_text(body, encoding="utf-8")


class TestDocFreshness(unittest.TestCase):

    def test_fresh_bootstrap_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _scaffold(root, "1.43.0")
            self.assertEqual(_run(root).returncode, 0)

    def test_general_doc_within_tier_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # README tier-3, 2 minors behind (1.43 vs 1.41) -> within budget
            _scaffold(root, "1.43.0",
                      {"README.md": "<!-- last-reviewed: 2026-05-01 v1.41.0 -->"})
            self.assertEqual(_run(root).returncode, 0)

    def test_security_doc_over_tier_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # SECURITY tier-1, 3 minors behind -> exceeds -> fail
            _scaffold(root, "1.43.0",
                      {"SECURITY.md": "<!-- last-reviewed: 2026-04-01 v1.40.0 -->"})
            self.assertEqual(_run(root).returncode, 1)

    def test_general_doc_over_tier_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # README tier-3, 4 minors behind -> exceeds -> fail
            _scaffold(root, "1.43.0",
                      {"README.md": "<!-- last-reviewed: 2026-03-01 v1.39.0 -->"})
            self.assertEqual(_run(root).returncode, 1)

    def test_override_passes_with_warning(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, "1.43.0",
                      {"SECURITY.md": "<!-- last-reviewed: 2026-04-01 v1.40.0 -->"})
            r = _run(root, waiver="emergency release E-123")
            self.assertEqual(r.returncode, 0, "waiver must bypass")
            self.assertIn("BYPASSED", r.stderr, "bypass must be surfaced, not silent")

    def test_malformed_stamp_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, "1.43.0",
                      {"SECURITY.md": "<!-- last-reviewed: garbage -->"})
            r = _run(root, json_mode=True)
            self.assertEqual(r.returncode, 1)
            data = json.loads(r.stdout)
            statuses = {x["doc"]: x["status"] for x in data["results"]}
            self.assertEqual(statuses["SECURITY.md"], "malformed-stamp")

    def test_absent_stamp_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, "1.43.0", {"SECURITY.md": None})  # no stamp at all
            r = _run(root, json_mode=True)
            self.assertEqual(r.returncode, 1)
            data = json.loads(r.stdout)
            statuses = {x["doc"]: x["status"] for x in data["results"]}
            self.assertEqual(statuses["SECURITY.md"], "absent-stamp")

    def test_json_shape_stable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _scaffold(root, "1.43.0")
            r = _run(root, json_mode=True)
            data = json.loads(r.stdout)
            self.assertIn("version", data)
            self.assertIn("results", data)
            self.assertIn("failures", data)
            self.assertIn("waiver", data)
            self.assertEqual(len(data["results"]), len(DOCS))

    def test_real_repo_docs_fresh(self):
        """Regression sentinel: the live repo's 7 stamped docs are fresh."""
        r = subprocess.run(
            ["python3", str(SCRIPT), "--repo-root", str(REPO_ROOT)],
            capture_output=True, text=True, timeout=30,
            env={k: v for k, v in os.environ.items()
                 if k != "CEO_DOC_FRESHNESS_WAIVER"},
        )
        self.assertEqual(r.returncode, 0, f"live docs stale; stdout={r.stdout}")


if __name__ == "__main__":
    unittest.main()
