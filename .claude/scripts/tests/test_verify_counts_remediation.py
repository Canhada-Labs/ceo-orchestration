"""verify-counts.sh E9-F10 recurrence-guard gate tests (PLAN-120-FOLLOWUP WS-B).

The E9-F10 finding showed verify-counts.sh had 3 blind spots that let the
lifecycle/version drift of E9-F1..F9 ship ungated:
  (i)   the recursive `_lib/**/*.py` count was never derived (top-level glob
        only) -> the "N recursive" literal in CLAUDE.md drifted (126 vs live
        127);
  (ii)  no ADR existence-by-status assertion -> ADR-127/128/131 (ACCEPTED,
        present) were mislabelled RESERVED and ADR-130/134 (genuinely
        reserved, absent) were not asserted-absent;
  (iii) no VERSION-string coherence -> CLAUDE.md said VERSION=1.46.0 while the
        live VERSION file said 1.46.1.

These tests assert each NEW gate FAILS on a synthetic drift and PASSES on a
clean synthetic tree, plus a live-tree regression sentinel that the real repo
passes all three gates (which depends on the companion CLAUDE.md doc-fix
landing in the same bundle).

The script is pointed at a synthetic tree via VERIFY_COUNTS_ROOT and run with
--no-tests so the slow pytest-collect is skipped. stdlib-only; py>=3.9.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "verify-counts.sh"


def _run(root: Optional[Path] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if root is not None:
        env["VERIFY_COUNTS_ROOT"] = str(root)
    args = ["bash", str(SCRIPT), "--no-tests"]
    return subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)


def _mk(n: int, make_one) -> None:
    for i in range(n):
        make_one(i)


def _scaffold(
    root: Path,
    *,
    core: int = 3,
    frontend: int = 2,
    domain: int = 4,
    adrs: int = 5,
    hook_py: int = 4,
    lib_top: int = 6,
    lib_nested: int = 2,
    registered: int = 3,
    spec: int = 2,
    version: str = "9.9.9",
    recursive_literal: Optional[int] = None,
    reserved_list: str = "130/134",
    adr127_status: str = "ACCEPTED",
    omit_adr131: bool = False,
    create_adr130: bool = False,
    claude_version: Optional[str] = None,
    install_version: Optional[str] = None,
    pkg_version: Optional[str] = None,
) -> None:
    """Build a minimal tree that satisfies the BASE gates, then layer in the
    E9-F10 inputs so the 3 new gates have something to check.

    `recursive_literal` defaults to the true recursive count (lib_top +
    lib_nested) so the clean tree passes; override it to force drift.
    """
    sk = root / ".claude" / "skills"
    _mk(core, lambda i: (sk / "core" / f"c{i}").mkdir(parents=True))
    _mk(core, lambda i: (sk / "core" / f"c{i}" / "SKILL.md").write_text("x", encoding="utf-8"))
    _mk(frontend, lambda i: (sk / "frontend" / f"f{i}").mkdir(parents=True))
    _mk(frontend, lambda i: (sk / "frontend" / f"f{i}" / "SKILL.md").write_text("x", encoding="utf-8"))
    _mk(domain, lambda i: (sk / "domains" / "d" / f"s{i}").mkdir(parents=True))
    _mk(domain, lambda i: (sk / "domains" / "d" / f"s{i}" / "SKILL.md").write_text("x", encoding="utf-8"))

    adr = root / ".claude" / "adr"
    adr.mkdir(parents=True)
    _mk(adrs, lambda i: (adr / f"ADR-{i:03d}-x.md").write_text("x", encoding="utf-8"))
    # ADR existence-by-status fixtures (E9-F10 ii).
    (adr / "ADR-127-pair-rail.md").write_text(
        f"---\nid: ADR-127\nstatus: {adr127_status}\n---\nbody\n", encoding="utf-8"
    )
    (adr / "ADR-128-c2.md").write_text(
        "---\nid: ADR-128\nstatus: ACCEPTED\n---\nbody\n", encoding="utf-8"
    )
    if not omit_adr131:
        (adr / "ADR-131-c5.md").write_text(
            "---\nid: ADR-131\nstatus: ACCEPTED\n---\nbody\n", encoding="utf-8"
        )
    if create_adr130:
        (adr / "ADR-130-c3.md").write_text(
            "---\nid: ADR-130\nstatus: ACCEPTED\n---\nbody\n", encoding="utf-8"
        )

    hooks = root / ".claude" / "hooks"
    (hooks / "_lib").mkdir(parents=True)
    _mk(hook_py, lambda i: (hooks / f"check_{i}.py").write_text("x", encoding="utf-8"))
    _mk(lib_top, lambda i: (hooks / "_lib" / f"mod_{i}.py").write_text("x", encoding="utf-8"))
    # Nested _lib modules (adapters/ + subdirs) so recursive > top-level.
    nested = hooks / "_lib" / "adapters"
    nested.mkdir(parents=True)
    _mk(lib_nested, lambda i: (nested / f"a{i}.py").write_text("x", encoding="utf-8"))

    spec_dir = root / "SPEC" / "v1"
    spec_dir.mkdir(parents=True)
    _mk(spec, lambda i: (spec_dir / f"s{i}.md").write_text("x", encoding="utf-8"))

    cmds = "\n".join(
        f'      {{"command": "bash _python-hook.sh reg_{i}.py"}},' for i in range(registered)
    )
    (hooks.parent / "settings.json").write_text(
        '{ "hooks": {\n' + cmds + "\n} }\n", encoding="utf-8"
    )

    # VERSION file (E9-F10 iii single source of truth).
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")

    rec = recursive_literal if recursive_literal is not None else (lib_top + lib_nested)
    cv = claude_version if claude_version is not None else version
    total = core + frontend + domain
    claude = (
        f"{total} reusable skills organized into `core/` ({core} universal), "
        f"`frontend/` ({frontend} universal frontend), {domain} domain across 29 profiles.\n"
        f"{adrs + 3} ADRs total on disk.\n"
        f"{hook_py} hook scripts on disk / {registered} registered hooks in settings.json.\n"
        f"{lib_top} shared modules under `_lib/` ({rec} recursive incl. adapters).\n"
        f"ADR-{reserved_list} RESERVED (no file, first-arrival stubs).\n"
        f"SPEC v1 + `VERSION={cv}`\n"
    )
    (root / "CLAUDE.md").write_text(claude, encoding="utf-8")
    (root / "README.md").write_text(f"{total} reusable skills here.\n", encoding="utf-8")
    iv = install_version if install_version is not None else version
    (root / "INSTALL.md").write_text(
        f"adds {core} universal core skills\n"
        f"bash scripts/upgrade.sh /path --pin v{iv}\n",
        encoding="utf-8",
    )
    npm = root / "npm"
    npm.mkdir(parents=True)
    pv = pkg_version if pkg_version is not None else version
    (npm / "package.json").write_text(
        '{\n  "name": "@x/y",\n  "version": "' + pv + '"\n}\n', encoding="utf-8"
    )


class TestE9F10RecurrenceGuards(unittest.TestCase):

    # ---- clean synthetic tree: ALL gates pass ----
    def test_clean_synthetic_tree_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root)
            r = _run(root)
            self.assertEqual(r.returncode, 0, f"clean tree must pass; stdout={r.stdout}\nstderr={r.stderr}")

    # ---- (i) recursive _lib gate ----
    def test_recursive_lib_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # live recursive = lib_top(6)+lib_nested(2)=8, but doc claims 7.
            _scaffold(root, lib_top=6, lib_nested=2, recursive_literal=7)
            r = _run(root)
            self.assertEqual(r.returncode, 1, "recursive _lib drift must fail the gate")
            self.assertIn("lib_recursive", r.stdout)

    def test_recursive_lib_add_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, lib_top=6, lib_nested=2)  # doc recursive=8, matches
            self.assertEqual(_run(root).returncode, 0)
            # add a nested module on disk -> live recursive=9, doc still says 8
            (root / ".claude" / "hooks" / "_lib" / "adapters" / "extra.py").write_text(
                "x", encoding="utf-8"
            )
            self.assertEqual(_run(root).returncode, 1, "a nested _lib add must be detected")

    # ---- (ii) ADR existence-by-status gate ----
    def test_reserved_adr_present_on_disk_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, create_adr130=True)  # ADR-130 must be ABSENT
            r = _run(root)
            self.assertEqual(r.returncode, 1, "a present RESERVED ADR (130) must fail")
            self.assertIn("ADR-130", r.stdout)

    def test_accepted_adr_missing_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, omit_adr131=True)  # ADR-131 must be present
            r = _run(root)
            self.assertEqual(r.returncode, 1, "a missing ACCEPTED ADR (131) must fail")
            self.assertIn("ADR-131", r.stdout)

    def test_accepted_adr_wrong_status_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, adr127_status="PROPOSED")  # 127 must be ACCEPTED
            r = _run(root)
            self.assertEqual(r.returncode, 1, "a non-ACCEPTED capability ADR (127) must fail")
            self.assertIn("ADR-127", r.stdout)

    def test_reserved_list_drift_in_claude_md_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # CLAUDE.md cites the OLD wrong RESERVED set (the exact E9-F1..F5 drift).
            _scaffold(root, reserved_list="127/128/130/131/134")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "RESERVED-list drift in CLAUDE.md must fail")
            self.assertIn("RESERVED", r.stdout)

    # ---- (iii) VERSION coherence gate ----
    def test_claude_md_version_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # live VERSION=9.9.9 but CLAUDE.md says 9.9.8 (the exact E9-F9 shape).
            _scaffold(root, version="9.9.9", claude_version="9.9.8")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "CLAUDE.md VERSION drift must fail")
            self.assertIn("version", r.stdout.lower())

    def test_install_md_pin_version_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, version="9.9.9", install_version="9.9.0")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "INSTALL.md --pin version drift must fail")

    def test_package_json_version_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, version="9.9.9", pkg_version="9.9.0")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "npm/package.json version drift must fail")

    # ---- live-tree regression sentinel: the real repo passes all 3 gates ----
    # NOTE: depends on the companion CLAUDE.md doc-fix (recursive 127, RESERVED
    # {130,134}, VERSION=1.46.1) landing in the same bundle. If this test fails,
    # the doc-fix has not been applied yet.
    def test_real_repo_passes_new_gates(self):
        r = _run(root=None)
        self.assertEqual(
            r.returncode,
            0,
            f"live tree must pass the E9-F10 gates (apply the CLAUDE.md doc-fix); stdout={r.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
