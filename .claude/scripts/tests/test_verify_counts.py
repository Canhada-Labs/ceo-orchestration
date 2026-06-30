"""verify-counts.sh hardened-gate unit tests.

PLAN-112-FOLLOWUP-claude-md-count-drift W4 / AC5 — covers the bidirectional
+ cross-file count gate that closes F-3-3.1 / F-4-docs-001.

Cases (AC5): clean tree passes / wrong number fails / a `_lib` add bumps the
count (proves `_lib` is counted) / cross-file mismatch fails. Plus the live
repo's own docs pass (regression sentinel for the S161 reconciliation).

The script is pointed at a synthetic tree via VERIFY_COUNTS_ROOT and run with
--no-tests so the slow pytest-collect is skipped.
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "verify-counts.sh"


def _run(root: Path | None = None, no_tests: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if root is not None:
        env["VERIFY_COUNTS_ROOT"] = str(root)
    args = ["bash", str(SCRIPT), "--quiet"]
    if no_tests:
        args.append("--no-tests")
    return subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)


def _mk(n: int, make_one) -> None:
    for i in range(n):
        make_one(i)


def _scaffold(root: Path, *, core=3, frontend=2, domain=4, adrs=5,
              hook_py=4, lib=6, registered=3, spec=2) -> dict:
    """Build a minimal live tree and return the derived counts."""
    sk = root / ".claude" / "skills"
    _mk(core, lambda i: (sk / "core" / f"c{i}").mkdir(parents=True))
    _mk(core, lambda i: (sk / "core" / f"c{i}" / "SKILL.md").write_text("x", encoding="utf-8"))
    _mk(frontend, lambda i: (sk / "frontend" / f"f{i}").mkdir(parents=True))
    _mk(frontend, lambda i: (sk / "frontend" / f"f{i}" / "SKILL.md").write_text("x", encoding="utf-8"))
    _mk(domain, lambda i: (sk / "domains" / "d" / f"s{i}").mkdir(parents=True))
    _mk(domain, lambda i: (sk / "domains" / "d" / f"s{i}" / "SKILL.md").write_text("x", encoding="utf-8"))

    adr = root / ".claude" / "adr"; adr.mkdir(parents=True)
    _mk(adrs, lambda i: (adr / f"ADR-{i:03d}-x.md").write_text("x", encoding="utf-8"))

    hooks = root / ".claude" / "hooks"; (hooks / "_lib").mkdir(parents=True)
    _mk(hook_py, lambda i: (hooks / f"check_{i}.py").write_text("x", encoding="utf-8"))
    _mk(lib, lambda i: (hooks / "_lib" / f"mod_{i}.py").write_text("x", encoding="utf-8"))

    spec_dir = root / "SPEC" / "v1"; spec_dir.mkdir(parents=True)
    _mk(spec, lambda i: (spec_dir / f"s{i}.md").write_text("x", encoding="utf-8"))

    # settings.json with `registered` distinct hook .py in "command" lines.
    cmds = "\n".join(
        f'      {{"command": "bash _python-hook.sh reg_{i}.py"}},' for i in range(registered)
    )
    (hooks.parent / "settings.json").write_text(
        '{ "hooks": {\n' + cmds + "\n} }\n", encoding="utf-8"
    )
    total = core + frontend + domain
    return dict(total=total, core=core, frontend=frontend, domain=domain,
                adrs=adrs, hook_py=hook_py, lib=lib, registered=registered)


def _write_docs(root: Path, *, total, core, frontend, domain, adrs,
                hook_py, lib, registered, readme_total=None) -> None:
    claude = (
        f"{total} reusable skills organized into `core/` ({core} universal), "
        f"`frontend/` ({frontend} universal frontend), {domain} domain across 29 profiles.\n"
        f"{adrs} ADRs total on disk.\n"
        f"{hook_py} hook scripts on disk / {registered} registered hooks in settings.json.\n"
        f"{lib} shared modules under `_lib/`.\n"
    )
    (root / "CLAUDE.md").write_text(claude, encoding="utf-8")
    rt = readme_total if readme_total is not None else total
    (root / "README.md").write_text(f"{rt} reusable skills here.\n", encoding="utf-8")
    (root / "INSTALL.md").write_text(f"adds {core} universal core skills\n", encoding="utf-8")


class TestVerifyCounts(unittest.TestCase):

    def test_clean_tree_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            r = _run(root)
            self.assertEqual(r.returncode, 0, f"expected clean pass; stdout={r.stdout}")

    def test_wrong_number_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            bad = dict(c); bad["total"] = c["total"] + 7   # doc lies about skills
            _write_docs(root, **bad)
            r = _run(root)
            self.assertEqual(r.returncode, 1, "wrong skills count must fail the gate")

    def test_lib_delta_bumps_count(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root, lib=6)
            _write_docs(root, **c)
            self.assertEqual(_run(root).returncode, 0)
            # add a 7th _lib module on disk; the doc still says 6 -> drift
            (root / ".claude" / "hooks" / "_lib" / "mod_new.py").write_text("x", encoding="utf-8")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "_lib add must be detected (counted)")

    def test_cross_file_mismatch_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            # README cites a different (wrong) skills total than the live tree
            _write_docs(root, readme_total=c["total"] - 1, **c)
            r = _run(root)
            self.assertEqual(r.returncode, 1, "cross-file disagreement must fail")

    def test_real_repo_docs_pass(self):
        """Regression sentinel: live CLAUDE.md/README/INSTALL match live counts."""
        r = _run(root=None)  # default REPO_ROOT, --no-tests
        self.assertEqual(r.returncode, 0, f"live docs drift; stdout={r.stdout}")


if __name__ == "__main__":
    unittest.main()
