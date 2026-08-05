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

import json
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

    # settings.json hooks{} SUBTREE with `registered` distinct hook .py
    # entries — VALID JSON (the S287 fix parses the subtree instead of
    # grepping the whole file). The top-level statusLine decoy references a
    # hyphenated .py OUTSIDE hooks{}: the old whole-file grep mangled it
    # into a phantom `ceo.py` and over-counted; the subtree parse must
    # ignore it entirely.
    settings = {
        "statusLine": {"type": "command", "command": "python3 statusline-ceo.py"},
        "hooks": {
            "PreToolUse": [{
                "matcher": "*",
                "hooks": [
                    {"command": f"bash _python-hook.sh reg_{i}.py"}
                    for i in range(registered)
                ],
            }]
        },
    }
    (hooks.parent / "settings.json").write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
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
        """Regression sentinel: live CLAUDE.md/README/INSTALL match live counts.

        PLAN-161 V1: the scan set now also covers docs/ARCHITECTURE.md,
        docs/GUIA-COMPLETO.md, docs/FAQ.md and npm/README.md — the four docs
        that drifted silently twice (S275, S278).
        """
        r = _run(root=None)  # default REPO_ROOT, --no-tests
        self.assertEqual(r.returncode, 0, f"live docs drift; stdout={r.stdout}")

    def test_statusline_decoy_not_counted(self):
        """S287 phantom-`ceo.py` class: a hyphenated .py referenced OUTSIDE
        the hooks{} subtree (statusLine) must not inflate `registered`.

        The scaffold docs cite what the old whole-file grep derived
        (registered + 1 phantom); the subtree parse derives `registered`,
        so the inflated doc claim MUST now fail the gate."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root, registered=3)
            inflated = dict(c)
            inflated["registered"] = c["registered"] + 1  # the phantom count
            _write_docs(root, **inflated)
            r = _run(root)
            self.assertEqual(
                r.returncode, 1,
                "doc citing the grep-era phantom count must fail against the "
                f"subtree-parsed truth; stdout={r.stdout}")

    # PER-DOCUMENT expectation set (pair-rail R3, P2). Aggregate liveness
    # is a FLOOR: a metric matching 5 of 6 watched docs looks alive while
    # the 6th drifts — exactly how docs/GUIA-COMPLETO.md sat stale at 44
    # hooks AFTER the metric-level rule was "fixed". These pairs are the
    # sites that actually carry each claim today; dropping one is a
    # silent coverage loss, so it must fail here and be re-ratified
    # deliberately (add/remove a pair) rather than vanish.
    # EXHAUSTIVE manifest, with EXACT counts (pair-rail R5). Two earlier
    # shapes of this guard were still vacuous:
    #   - covering 3 metrics of the 54 live pairs left every unlisted
    #     claim (skills@INSTALL.md, hook_py@CLAUDE.md, …) able to drift
    #     while aggregate rule_matches stayed nonzero from other docs;
    #   - asserting PRESENCE (>=1) let a doc carrying TWO independent
    #     claims for one metric (registered@docs/ARCHITECTURE.md: table +
    #     prose) lose one silently.
    # So: every pair, with its exact count. Editing a watched doc is
    # SUPPOSED to fail here — that forces the manifest to be re-ratified
    # deliberately instead of coverage evaporating unnoticed. Regenerate
    # with: verify-counts.sh --json --no-tests | jq .rule_matches_by_doc
    # RE-RATIFIED at the PLAN-166 W0 reconciliation: the W0 doc pass added
    # count claims to README.pt-BR.md, docs/CTO-GUIDE.md, docs/README.md,
    # docs/WHAT-WE-ARE.md, docs/FAQ.md and npm/README.md, growing the census
    # from 54 to 109 pairs. Regenerated from the gate itself (never typed from
    # memory); the ratification asserted ZERO lost and ZERO shrunk pairs
    # first, so coverage only widened.
    _EXPECTED_SITES = {
        "adrs@README.md": 2,
        "adrs@README.pt-BR.md": 2,
        "adrs@docs/ARCHITECTURE.md": 1,
        "adrs@docs/CTO-GUIDE.md": 3,
        "adrs@docs/FAQ.md": 1,
        "adrs@docs/README.md": 1,
        "adrs@npm/README.md": 2,
        "commands@CLAUDE.md": 1,
        "commands@README.md": 2,
        "commands@README.pt-BR.md": 2,
        "commands@docs/ARCHITECTURE.md": 2,
        "commands@docs/FAQ.md": 1,
        "commands@docs/README.md": 1,
        "commands@npm/README.md": 2,
        "core@CLAUDE.md": 2,
        "core@INSTALL.md": 3,
        "core@README.md": 1,
        "core@README.pt-BR.md": 1,
        "core@docs/CTO-GUIDE.md": 2,
        "core@docs/FAQ.md": 2,
        "core@docs/README.md": 2,
        "core@docs/WHAT-WE-ARE.md": 1,
        "core@npm/README.md": 1,
        "domain@CLAUDE.md": 1,
        "domain@INSTALL.md": 2,
        "domain@README.md": 1,
        "domain@README.pt-BR.md": 1,
        "domain@docs/ARCHITECTURE.md": 1,
        "domain@docs/CTO-GUIDE.md": 1,
        "domain@docs/FAQ.md": 1,
        "domain@docs/README.md": 1,
        "domain@docs/WHAT-WE-ARE.md": 1,
        "domain@npm/README.md": 1,
        "frontend@CLAUDE.md": 1,
        "frontend@INSTALL.md": 3,
        "frontend@README.md": 1,
        "frontend@README.pt-BR.md": 1,
        "frontend@docs/ARCHITECTURE.md": 1,
        "frontend@docs/CTO-GUIDE.md": 1,
        "frontend@docs/FAQ.md": 1,
        "frontend@docs/README.md": 1,
        "frontend@npm/README.md": 1,
        "hook_py@CLAUDE.md": 1,
        "hook_py@INSTALL.md": 1,
        "hook_py@README.md": 1,
        "hook_py@README.pt-BR.md": 2,
        "hook_py@docs/ARCHITECTURE.md": 2,
        "hook_py@docs/CTO-GUIDE.md": 1,
        "hook_py@docs/README.md": 1,
        "hook_py@npm/README.md": 2,
        "lib@INSTALL.md": 2,
        "lib@README.md": 1,
        "lib@README.pt-BR.md": 1,
        "lib@docs/ARCHITECTURE.md": 2,
        "lib@docs/CTO-GUIDE.md": 1,
        "lib@docs/README.md": 1,
        "lib@npm/README.md": 1,
        "lib_recursive@docs/ARCHITECTURE.md": 2,
        "mutation_fixtures@docs/CTO-GUIDE.md": 2,
        "registered@CLAUDE.md": 1,
        "registered@README.md": 1,
        "registered@README.pt-BR.md": 2,
        "registered@docs/ARCHITECTURE.md": 2,
        "registered@docs/CTO-GUIDE.md": 2,
        "registered@docs/GUIA-COMPLETO.md": 1,
        "registered@docs/README.md": 1,
        "registered@npm/README.md": 1,
        "registrations@CLAUDE.md": 1,
        "registrations@README.md": 1,
        "registrations@README.pt-BR.md": 1,
        "registrations@docs/ARCHITECTURE.md": 1,
        "registrations@docs/CTO-GUIDE.md": 1,
        "registrations@docs/README.md": 2,
        "registrations@npm/README.md": 1,
        "release_steps@RELEASE.md": 1,
        "schema_files@README.md": 1,
        "schema_files@README.pt-BR.md": 1,
        "schema_files@docs/ARCHITECTURE.md": 3,
        "schema_files@docs/CTO-GUIDE.md": 2,
        "schema_files@npm/README.md": 1,
        "skills@INSTALL.md": 1,
        "skills@README.md": 3,
        "skills@README.pt-BR.md": 3,
        "skills@docs/ARCHITECTURE.md": 1,
        "skills@docs/CTO-GUIDE.md": 1,
        "skills@docs/FAQ.md": 1,
        "skills@docs/README.md": 1,
        "skills@docs/WHAT-WE-ARE.md": 1,
        "skills@npm/README.md": 3,
        "spec_v1@README.pt-BR.md": 1,
        "spec_v1@docs/ARCHITECTURE.md": 1,
        "spec_v1@docs/CTO-GUIDE.md": 1,
        "test_files@CLAUDE.md": 1,
        "test_files@docs/ARCHITECTURE.md": 2,
        "test_files@docs/CTO-GUIDE.md": 1,
        "test_files@docs/README.md": 1,
        "tests@CLAUDE.md": 1,
        "tests@INSTALL.md": 1,
        "tests@README.md": 2,
        "tests@README.pt-BR.md": 2,
        "tests@docs/ARCHITECTURE.md": 3,
        "tests@docs/CTO-GUIDE.md": 2,
        "tests@docs/FAQ.md": 1,
        "tests@docs/GUIA-COMPLETO.md": 1,
        "tests@docs/README.md": 1,
        "tests@docs/WHAT-WE-ARE.md": 2,
        "tests@npm/README.md": 2,
        "tla_specs@docs/CTO-GUIDE.md": 1,
        "workflows@docs/CTO-GUIDE.md": 1,
    }

    def test_real_repo_per_document_liveness(self):
        """Every watched (metric, doc) pair must match its EXACT count.

        Both directions are failures: a pair that drops below its count
        is silent coverage loss; a pair that appears or grows without the
        manifest being updated is an unratified claim site."""
        r = subprocess.run(
            ["bash", str(SCRIPT), "--json", "--no-tests"],
            capture_output=True, text=True, timeout=60, env=os.environ.copy())
        self.assertEqual(r.returncode, 0, r.stdout)
        by_doc = json.loads(r.stdout).get("rule_matches_by_doc", {})
        # The dict diff is long and unreadable; the named lists below are
        # the actionable part, so show them rather than the raw diff.
        self.maxDiff = None
        self.assertEqual(
            by_doc, self._EXPECTED_SITES,
            "watched claim sites drifted from the ratified manifest. "
            "Lost: {0}. Unratified/new: {1}.".format(
                sorted(k for k in self._EXPECTED_SITES
                       if by_doc.get(k, 0) != self._EXPECTED_SITES[k]),
                sorted(k for k in by_doc if k not in self._EXPECTED_SITES),
            ))

    def test_real_repo_rule_liveness(self):
        """S287 vacuous-gate class: every doc-gated metric must match >=1
        site in the real repo's watched docs. A metric at 0 matches is a
        DEAD gate — it reports "no drift" with a number nobody compares
        (`registered` was dead from birth: derived 47 phantom, matched no
        doc, said "no drift" for months)."""
        env = os.environ.copy()
        r = subprocess.run(
            ["bash", str(SCRIPT), "--json", "--no-tests"],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout)
        self.assertIn("rule_matches", data)
        dead = sorted(k for k, v in data["rule_matches"].items() if v == 0)
        self.assertEqual(dead, [], f"dead doc-gate rules (0 matches): {dead}")


class TestTableCellRules(unittest.TestCase):
    """PLAN-161 V1 — the S275 miss class: number and label in SEPARATE
    markdown-table cells (`| ADRs | 178 |`), invisible to prose regexes."""

    def _with_table(self, adrs_cited: int):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            arch = root / "docs"
            arch.mkdir()
            (arch / "ARCHITECTURE.md").write_text(
                "| Component | Count | Verify |\n"
                "|---|---|---|\n"
                f"| ADRs | {adrs_cited} | `ls .claude/adr/ADR-*.md \\| wc -l` |\n",
                encoding="utf-8",
            )
            return _run(root)

    def test_seeded_table_cell_drift_is_caught(self):
        c_adrs = 5  # _scaffold default
        r = self._with_table(adrs_cited=c_adrs + 173)  # the S275 shape: 178 vs 5
        self.assertEqual(r.returncode, 1, "table-cell ADR drift must fail the gate")

    def test_correct_table_cell_passes(self):
        r = self._with_table(adrs_cited=5)
        self.assertEqual(r.returncode, 0, f"correct table cell must pass; {r.stdout}")

    def test_bold_wrapped_table_cell_drift_is_caught(self):
        """npm/README shape: label spelled out, value bold-wrapped in its own
        cell (`| Architecture decision records | **N** | ... |`)."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            npm = root / "npm"
            npm.mkdir()
            (npm / "README.md").write_text(
                "| Component | Count | Notes |\n"
                "|---|---|---|\n"
                "| Architecture decision records | **999** | under `.claude/adr/` |\n",
                encoding="utf-8",
            )
            r = _run(root)
            self.assertEqual(r.returncode, 1, "bold table-cell ADR drift must fail")


if __name__ == "__main__":
    unittest.main()
