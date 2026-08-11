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
        # PLAN-166 W2 rc.3: the scoped CHANGELOG header rule watches
        # exactly four counts in the header claim — see the
        # "CHANGELOG HEADER RULE (scoped)" block in verify-counts.sh.
        "adrs@CHANGELOG.md": 1,
        "commands@CHANGELOG.md": 1,
        "lib@CHANGELOG.md": 1,
        "skills@CHANGELOG.md": 1,
        "adrs@README.md": 2,
        "adrs@README.pt-BR.md": 2,
        "adrs@docs/ARCHITECTURE.md": 1,
        "adrs@docs/CTO-GUIDE.md": 3,
        "adrs@docs/FAQ.md": 1,
        # PLAN-169 W2.7: BOTH GUIA ADR-count phrases are watched — the
        # prose "N ADRs document ..." and the listing "N Architecture
        # Decision Records" (the 2nd was the repass-r2 part-e find).
        "adrs@docs/GUIA-COMPLETO.md": 2,
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
        # PLAN-166 W0 re-pass: the §1.4 phrase wraps across a newline
        # ("8 frontend (universal\nfrontend)") — the matcher is now \s+
        # tolerant, so the site exists for the first time.
        "frontend@docs/WHAT-WE-ARE.md": 1,
        "frontend@npm/README.md": 1,
        "hook_py@CLAUDE.md": 1,
        "hook_py@INSTALL.md": 1,
        "hook_py@README.md": 1,
        "hook_py@README.pt-BR.md": 2,
        "hook_py@docs/ARCHITECTURE.md": 2,
        "hook_py@docs/CTO-GUIDE.md": 1,
        # PLAN-166 W0 re-pass: 1 -> 2. The table row plus the prose site
        # "the **57** hook\nscripts on disk" (bold-wrapped AND line-wrapped;
        # the plain regex saw only the table row).
        "hook_py@docs/README.md": 2,
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
        # PLAN-166 W0 re-pass: 1 -> 3. The bold-tolerant "distinct scripts"
        # matcher now sees the "**46** distinct scripts" prose site AND the
        # same phrase inside the "Hooks registered" table value cell (which
        # the table rule also reads — both compare to the same live value).
        "registered@docs/README.md": 3,
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


def _run_json(root: Path, no_tests: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["VERIFY_COUNTS_ROOT"] = str(root)
    args = ["bash", str(SCRIPT), "--json"]
    if no_tests:
        args.append("--no-tests")
    return subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)


def _pytest_scaffold(root: Path, cases: int = 100, broken: bool = False) -> None:
    """Give the synthetic tree a REAL pytest-collect population so the gate's
    full run (no --no-tests) derives a live `tests` value inside the tree."""
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n",
                                     encoding="utf-8")
    tdir = root / "tests"
    tdir.mkdir(exist_ok=True)
    (tdir / "test_ok.py").write_text(
        "import pytest\n"
        f"@pytest.mark.parametrize('i', range({cases}))\n"
        "def test_p(i):\n    pass\n",
        encoding="utf-8",
    )
    if broken:
        (tdir / "test_broken.py").write_text(
            "import module_that_does_not_exist_plan166_repass\n",
            encoding="utf-8",
        )


class TestPlan166RepassFindings(unittest.TestCase):
    """PLAN-166 W0 adversarial re-pass — each test here is the red/green
    proof for one finding against the gate itself (findings 1-5, 7)."""

    def test_unmatched_thousands_numeral_fails_gate(self):
        """Finding 1: an unmatched thousands-shaped numeral in a watched doc
        must FAIL the gate. As a warning it was invisible to every automated
        caller (validate.yml --quiet, release preflight >/dev/null)."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("handles ~9k widgets in the steady state.\n")
            r = _run_json(root)
            self.assertEqual(r.returncode, 1,
                             f"unmatched ~9k must fail the gate; {r.stdout}")
            data = json.loads(r.stdout)
            self.assertTrue(
                any("unmatched-sweep" in v for v in data["violations"]),
                f"expected an approx/unmatched-sweep VIOLATION; {data}")

    def test_unmatched_decimal_k_numeral_fails_gate(self):
        """W0 re-pass round 2: the sweep was blind to decimal-k thousands
        forms — an unmatched '~1.4k' (EN decimal) or '~13,5k' (pt decimal)
        in a watched doc shipped with EXIT=0 while '~9k' failed, even
        though round-1 finding 7 taught approx_norm the very same shape
        (red proof, pre-fix: '~1.4k widgets' planted in the live README.md
        ran the gate to EXIT=0). Both decimal shapes must now be swept."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            with open(root / "README.md", "a", encoding="utf-8") as f:
                f.write("handles ~1.4k widgets in steady state.\n")
            (root / "README.pt-BR.md").write_text(
                "processa ~13,5k unidades por dia.\n", encoding="utf-8")
            r = _run_json(root)
            self.assertEqual(
                r.returncode, 1,
                f"unmatched decimal-k numerals must fail the gate; {r.stdout}")
            vio = json.loads(r.stdout)["violations"]
            self.assertTrue(
                any("unmatched-sweep" in v and "~1.4k" in v for v in vio),
                f"expected a swept ~1.4k violation; {vio}")
            self.assertTrue(
                any("unmatched-sweep" in v and "~13,5k" in v for v in vio),
                f"expected a swept ~13,5k violation; {vio}")

    def test_stale_pending_value_is_not_grandfathered(self):
        """Finding 2: the consumed (CLAUDE.md, tests, 13000) APPROX_PENDING
        entry is gone — a CLAUDE.md citing '~13,000 parametrized cases'
        against a live collect far outside the band must fail the FULL run.
        With the entry present this exact configuration exited 0 (PENDING),
        because the pending lookup ran BEFORE the band check."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            _pytest_scaffold(root, cases=200)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("collect reports ~13,000 parametrized cases.\n")
            r = _run_json(root, no_tests=False)
            self.assertEqual(
                r.returncode, 1,
                f"stale 13,000 vs live 200 must fail, never PEND; {r.stdout}")
            data = json.loads(r.stdout)
            self.assertEqual(data["pending"], [],
                             "no site may be silently exempted")
            self.assertTrue(
                any("tests=~13000" in v and "band" in v
                    for v in data["violations"]),
                f"expected an approx band violation; {data['violations']}")

    def test_bold_wrapped_prose_counts_are_watched(self):
        """Finding 3: '**N** distinct scripts' and the line-wrapped
        '**N** hook\\nscripts' prose sites were invisible to the plain-space
        regexes (dead-regex class) — drift there must now fail."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)  # registered=3, hook_py=4
            _write_docs(root, **c)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("wired as **999** distinct scripts today.\n")
                f.write("the **888** hook\nscripts on disk are canonical.\n")
            r = _run_json(root)
            self.assertEqual(r.returncode, 1, f"bold drift must fail; {r.stdout}")
            vio = "\n".join(json.loads(r.stdout)["violations"])
            self.assertIn("registered=999", vio)
            self.assertIn("hook_py=888", vio)

    def test_line_wrapped_frontend_tier_is_watched(self):
        """Finding 4: 'N frontend (universal\\nfrontend)' wraps across a
        newline in docs/WHAT-WE-ARE.md §1.4; the literal-space regex matched
        ZERO sites while core/domain in the same sentence were watched."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)  # frontend=2
            _write_docs(root, **c)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("tiers: 9 frontend (universal\nfrontend) skills.\n")
            r = _run_json(root)
            self.assertEqual(
                r.returncode, 1,
                f"line-wrapped frontend drift must fail; {r.stdout}")
            self.assertTrue(
                any("frontend=9" in v
                    for v in json.loads(r.stdout)["violations"]))

    def test_collect_errors_fail_when_band_enforced(self):
        """Finding 5: collection errors mean the band verdict is computed
        over a PARTIAL population. When the band was enforced over >=1 site
        this run, that must be a VIOLATION — the only automated full-run
        caller (release preflight) discards all output, so a warning is
        structurally invisible. Positive control: the identical tree with a
        clean collect passes, so the failure is attributable to the error."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            _pytest_scaffold(root, cases=100, broken=False)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("collect reports ~100 parametrized cases.\n")
            r = _run_json(root, no_tests=False)
            self.assertEqual(r.returncode, 0,
                             f"clean-collect control must pass; {r.stdout}")
            (root / "tests" / "test_broken.py").write_text(
                "import module_that_does_not_exist_plan166_repass\n",
                encoding="utf-8")
            r = _run_json(root, no_tests=False)
            self.assertEqual(
                r.returncode, 1,
                f"in-band cite over a partial collect must fail; {r.stdout}")
            self.assertTrue(
                any("collect-errors" in v
                    for v in json.loads(r.stdout)["violations"]),
                f"expected approx/collect-errors violation; {r.stdout}")

    def test_decimal_k_normalizes_to_hundreds_not_tenfold(self):
        """Finding 7: approx_norm parsed '~1.4k' as 14000 (separator-strip
        after the k-multiplier) — a 10x error in the FALSE-PASS direction.
        Cross-doc equality proves the parse: '~1400' and '~1.4k' are the
        SAME claim and must normalize to the same integer (1400)."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            with open(root / "CLAUDE.md", "a", encoding="utf-8") as f:
                f.write("collect reports ~1400 tests.\n")
            with open(root / "README.md", "a", encoding="utf-8") as f:
                f.write("collect reports ~1.4k tests.\n")
            r = _run_json(root)
            self.assertEqual(
                r.returncode, 0,
                f"~1400 and ~1.4k are the same figure — must pass; {r.stdout}")
            cited = sorted(set(
                s["cited"] for s in json.loads(r.stdout)["approx"]["sites"]
                if s["metric"] == "tests"))
            self.assertEqual(cited, [1400],
                             f"decimal-k must normalize to 1400; got {cited}")


class TestPtBrLabelControls(unittest.TestCase):
    """PLAN-166 W0 AC-5 positive controls, pt-BR leg (W0 re-pass round 2).

    The _EXPECTED_SITES manifest proves the pt-BR matchers MATCH (liveness:
    _note() fires before the enforce branch) — it does NOT prove a match
    ENFORCES. A kind-binding bug could keep the manifest green while
    enforcement silently died. These controls plant a WRONG number at every
    watched pt-BR label/phrasing of README.pt-BR.md and demand one named
    violation per plant, preceded by a clean-control run so each failure is
    attributable to its plant, not to the phrasing.

    The metric list is DERIVED from the manifest keys ending in
    '@README.pt-BR.md' — never a recalled list (the numeral-espelho lesson:
    recited enumerations failed 4x in this plan) — so ratifying a new pt
    site into the manifest without adding its control phrasing fails here
    first, in the coverage test below.
    """

    _PT_DOC = "README.pt-BR.md"

    # metric -> snippet factory carrying that metric's watched pt-BR
    # phrasing(s) with the given (planted) value. Phrasings mirror the live
    # sites in README.pt-BR.md: the four pt table labels (Checklists de
    # skills / Scripts de hook / Hooks ligados em / Módulos de biblioteca
    # compartilhada) and the pt prose forms (arquivos de skill / em disco /
    # ligados / registros de evento / core-frontend-de domínio split /
    # SPEC-v1 arquivos / `*.schema.md` / '# N ADRs' / N slash commands).
    _EXACT_PLANTS = {
        "skills": lambda v: (
            "| Checklists de skills | **%d** | x |\n"
            "entrega **%d arquivos de skill** reutilizáveis.\n" % (v, v)),
        "core": lambda v: "organizadas em %d core + outros tiers.\n" % v,
        "frontend": lambda v: "mais %d frontend + o resto.\n" % v,
        "domain": lambda v: "e + %d de domínio no total.\n" % v,
        "adrs": lambda v: "ls .claude/adr  # %d ADRs\n" % v,
        "commands": lambda v: (
            "%d slash commands em `.claude/commands/`.\n" % v),
        "hook_py": lambda v: (
            "| Scripts de hook (em disco) | **%d** | x |\n"
            "a diferença entre **%d em disco** e os ligados.\n" % (v, v)),
        "registered": lambda v: (
            "| Hooks ligados em `settings.json` | **%d** | x |\n"
            "são **%d ligados** no total.\n" % (v, v)),
        "registrations": lambda v: "com %d registros de evento.\n" % v,
        "lib": lambda v: (
            "| Módulos de biblioteca compartilhada | **%d** | x |\n" % v),
        "spec_v1": lambda v: (
            "contrato em `SPEC/v1/` (%d arquivos — fixado).\n" % v),
        "schema_files": lambda v: (
            "sendo %d `*.schema.md` de contrato.\n" % v),
    }
    # `tests` is approx-kind: a wrong EXACT integer is a different rule, so
    # its control is the out-of-band ~Nk plant below.
    _APPROX_CONTROLLED = {"tests"}

    def test_pt_control_coverage_is_derived_from_manifest(self):
        """Every metric the ratified manifest watches at README.pt-BR.md has
        a planted control here — and no control exists for an unwatched
        metric. Derived from _EXPECTED_SITES, never recited."""
        derived = sorted(set(
            k.split("@")[0] for k in TestVerifyCounts._EXPECTED_SITES
            if k.endswith("@" + self._PT_DOC)))
        covered = sorted(set(self._EXACT_PLANTS) | self._APPROX_CONTROLLED)
        self.assertEqual(
            covered, derived,
            "pt-BR positive-control coverage drifted from the ratified "
            "manifest: every metric watched at README.pt-BR.md needs a "
            "planted control (and none may be invented).")

    def test_wrong_number_at_each_pt_label_fails(self):
        """AC-5 control (a): a wrong number planted at EACH watched pt-BR
        label/phrasing must produce a named violation for that metric."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            clean = {  # live values of the _scaffold tree, per metric
                "skills": c["total"], "core": c["core"],
                "frontend": c["frontend"], "domain": c["domain"],
                "adrs": c["adrs"], "hook_py": c["hook_py"],
                "registered": c["registered"],
                # one command string per hook entry in the scaffold
                # settings.json, so registrations == registered there
                "registrations": c["registered"],
                "lib": c["lib"],
                "spec_v1": 2,       # _scaffold default: SPEC/v1/{s0,s1}.md
                "schema_files": 0,  # the scaffold ships no *.schema.md
                "commands": 0,      # the scaffold ships no .claude/commands/
            }
            self.assertEqual(sorted(clean), sorted(self._EXACT_PLANTS))
            pt = root / self._PT_DOC
            # Clean control: every phrasing planted with the CORRECT live
            # value passes, so the wrong-plant failures below are
            # attributable to the number, not the phrasing.
            pt.write_text(
                "".join(self._EXACT_PLANTS[m](clean[m])
                        for m in sorted(self._EXACT_PLANTS)),
                encoding="utf-8")
            r = _run_json(root)
            self.assertEqual(
                r.returncode, 0,
                f"clean pt-BR control must pass; {r.stdout}")
            # Wrong plants: a distinct value per metric so every violation
            # names its plant unambiguously.
            planted = dict(
                (m, 900 + i)
                for i, m in enumerate(sorted(self._EXACT_PLANTS)))
            pt.write_text(
                "".join(self._EXACT_PLANTS[m](planted[m])
                        for m in sorted(self._EXACT_PLANTS)),
                encoding="utf-8")
            r = _run_json(root)
            self.assertEqual(
                r.returncode, 1,
                f"planted pt-BR drift must fail the gate; {r.stdout}")
            vio = json.loads(r.stdout)["violations"]
            pt_vio = [v for v in vio if v.startswith(self._PT_DOC)]
            for m in sorted(planted):
                self.assertTrue(
                    any("%s=%d" % (m, planted[m]) in line
                        for line in pt_vio),
                    "planted %s=%d produced no %s violation; got: %s"
                    % (m, planted[m], self._PT_DOC, vio))

    def test_planted_out_of_band_nk_pt_site_fails_band(self):
        """AC-5 control (b): a CONSUMED approx site in the ~Nk form planted
        OUTSIDE the +/-5% band (~9k casos vs a real live collect of 200)
        must fail the approx BAND rule — and must NOT appear in the
        unmatched sweep, proving the plant exercised the consumed
        band-check path rather than being caught as an orphan numeral."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = _scaffold(root)
            _write_docs(root, **c)
            _pytest_scaffold(root, cases=200)
            (root / self._PT_DOC).write_text(
                "a coleta reporta ~9k casos hoje.\n", encoding="utf-8")
            r = _run_json(root, no_tests=False)
            self.assertEqual(
                r.returncode, 1,
                f"out-of-band ~9k vs live 200 must fail; {r.stdout}")
            data = json.loads(r.stdout)
            self.assertTrue(
                any("tests=~9000" in v and "OUTSIDE the +/-5% band" in v
                    for v in data["violations"]),
                f"expected an approx band violation; {data['violations']}")
            self.assertFalse(
                any("unmatched-sweep" in v for v in data["violations"]),
                "the ~9k site must be CONSUMED by the approx rule, "
                f"never swept; {data['violations']}")


class TestDocFreshness(unittest.TestCase):
    """PLAN-166 W0 re-pass finding 6: docs/CTO-GUIDE.md carried v0-era
    roadmap claims ('HMAC chain queued (DYN-SEC3 / Sprint 16)', Sprint 15-16
    gating, PLAN-017) under a fresh 'Last reviewed' stamp — the HMAC-chained
    audit log is a SHIPPED flagship feature. Non-numeric, so the count gate
    is blind by design; this tripwire stops the stale phrases from being
    resurrected by a merge-conflict resolution."""

    _STALE_MARKERS = (
        "HMAC chain queued",
        "DYN-SEC3",
        "Sprint 15-16",
        "Sprint 16",
        "post-Sprint-16",
        "PLAN-017",
    )

    def test_cto_guide_carries_no_v0_roadmap_markers(self):
        text = (REPO_ROOT / "docs" / "CTO-GUIDE.md").read_text(encoding="utf-8")
        found = [m for m in self._STALE_MARKERS if m in text]
        self.assertEqual(
            found, [],
            "docs/CTO-GUIDE.md still carries v0-era roadmap claims that "
            f"contradict shipped reality: {found}")


class TestChangelogHeaderRule(unittest.TestCase):
    """Scoped CHANGELOG header rule (PLAN-166 W2 rc.3, rail r1 P1-4).

    The rule enforces the four-count header claim in the PREAMBLE only
    (before the first "## [" release heading): exactly one claim, exact
    counts. Body claims are invisible BY CONSTRUCTION — the log's body
    carries historical counts on purpose — so they can neither satisfy
    a removed header nor duplicate the census site.
    """

    # Matches _scaffold defaults: skills total 9 (3+2+4), commands 0
    # (no .claude/commands dir), adrs 5, lib 6.
    _GOOD_CLAIM = (
        "counts below (as of\n"
        "v0.0.0: 9 skills, 0 slash commands, 5 ADRs, 6 `_lib` modules) are\n"
    )
    _STALE_CLAIM = (
        "v0.0.0: 9 skills, 0 slash commands, 4 ADRs, 6 `_lib` modules) were\n"
    )
    _BODY = "\n## [0.0.1] - 2000-01-01\n\nhistorical notes.\n"

    def _run_loud(self, tmp):
        # Sem --quiet: os casos de falha asserta(m) a MENSAGEM da
        # violation, que o modo quiet suprime.
        env = os.environ.copy()
        env["VERIFY_COUNTS_ROOT"] = str(tmp)
        return subprocess.run(
            ["bash", str(SCRIPT), "--no-tests"],
            capture_output=True, text=True, timeout=60, env=env)

    def _tree(self, tmp, chlog):
        import pathlib
        counts = _scaffold(pathlib.Path(tmp))
        _write_docs(pathlib.Path(tmp), **counts)
        if chlog is not None:
            (pathlib.Path(tmp) / "CHANGELOG.md").write_text(
                chlog, encoding="utf-8")

    def test_absent_changelog_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, None)
            r = _run(root=Path(tmp))
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_correct_header_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, self._GOOD_CLAIM + self._BODY)
            r = _run(root=Path(tmp))
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_wrong_header_count_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, self._STALE_CLAIM + self._BODY)
            r = self._run_loud(tmp)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("changelog/header", r.stdout)

    def test_body_only_claim_is_dead_matcher_violation(self):
        # A removed header cannot be masked by an exact-shaped claim in
        # the body (rail r1 P1-4's masking scenario).
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, "no claim up here.\n" + self._BODY
                       + self._GOOD_CLAIM)
            r = self._run_loud(tmp)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("changelog/header", r.stdout)
            self.assertIn("not found in the preamble", r.stdout)

    def test_duplicate_preamble_claims_fail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, self._GOOD_CLAIM + "\n" + self._GOOD_CLAIM
                       + self._BODY)
            r = self._run_loud(tmp)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("exactly one", r.stdout)

    def test_stale_body_claim_ignored_by_construction(self):
        # Historical counts in the body stay legitimate.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp, self._GOOD_CLAIM + self._BODY
                       + self._STALE_CLAIM)
            r = _run(root=Path(tmp))
            self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
