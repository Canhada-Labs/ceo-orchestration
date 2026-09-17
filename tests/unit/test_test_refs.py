"""Unit tests for ``.claude/scripts/test_refs.py`` (PLAN-190 W3) — the
name-vs-path class: references are normalised to node ids; ambiguous or
unknown references are errors, never silently accepted."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve()
while not (_REPO / ".claude").is_dir() or not (_REPO / "VERSION").is_file():
    if _REPO.parent == _REPO:
        raise RuntimeError("repo root not found")
    _REPO = _REPO.parent
sys.path.insert(0, str(_REPO / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = _REPO / ".claude" / "scripts" / "test_refs.py"

TREE = {
    "tests/test_alpha.py": "def test_one():\n    pass\n\ndef test_shared():\n    pass\n\nclass TestGroup:\n    def test_inner(self):\n        pass\n",
    "tests/sub/test_beta.py": "import unittest\n\nclass BetaCase(unittest.TestCase):\n    def test_two(self):\n        pass\n\ndef test_shared():\n    pass\n",
    "tests/helpers.py": "def not_a_test():\n    pass\n",
}


def _load_module():
    spec = importlib.util.spec_from_file_location("test_refs_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestRefsNormalize(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        for rel, body in TREE.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        self.tr = _load_module()

    def test_file_path_expands_to_all_nodes(self):
        out = self.tr.normalize(self.repo, ["tests/test_alpha.py"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["resolved"]["tests/test_alpha.py"],
                         ["tests/test_alpha.py::test_one", "tests/test_alpha.py::test_shared", "tests/test_alpha.py::TestGroup::test_inner"])

    def test_unique_function_name_resolves(self):
        out = self.tr.normalize(self.repo, ["test_one", "test_two"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["resolved"]["test_one"], ["tests/test_alpha.py::test_one"])
        self.assertEqual(out["resolved"]["test_two"], ["tests/sub/test_beta.py::BetaCase::test_two"])

    def test_ambiguous_function_name_is_an_error_with_candidates(self):
        out = self.tr.normalize(self.repo, ["test_shared"])
        self.assertEqual(len(out["errors"]), 1)
        err = out["errors"][0]
        self.assertEqual(err["kind"], "ambiguous")
        self.assertEqual(sorted(err["candidates"]), ["tests/sub/test_beta.py::test_shared", "tests/test_alpha.py::test_shared"])

    def test_unknown_name_and_missing_file_are_errors(self):
        out = self.tr.normalize(self.repo, ["test_nope", "tests/missing.py", "tests/test_alpha.py::test_nope"])
        kinds = sorted(e["kind"] for e in out["errors"])
        self.assertEqual(kinds, ["file-not-found", "node-not-found", "not-found"])

    def test_class_qualified_name_resolves(self):
        out = self.tr.normalize(self.repo, ["TestGroup.test_inner", "BetaCase::test_two"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["resolved"]["TestGroup.test_inner"], ["tests/test_alpha.py::TestGroup::test_inner"])

    def test_non_test_file_has_no_nodes(self):
        out = self.tr.normalize(self.repo, ["tests/helpers.py"])
        self.assertEqual(out["errors"][0]["kind"], "file-not-found")


class TestRefsMatchCLI(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        for rel, body in TREE.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

    def _run(self, declared, proved):
        d = self.repo / "declared.txt"; d.write_text("\n".join(declared) + "\n", encoding="utf-8")
        p = self.repo / "proved.json"; p.write_text(json.dumps(proved), encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), "match", "--repo", str(self.repo), "--declared", str(d), "--proved", str(p)],
                              capture_output=True, text=True, timeout=60)

    def test_function_names_and_paths_match_after_normalisation(self):
        r = self._run(["test_one", "tests/sub/test_beta.py::BetaCase::test_two"], ["tests/test_alpha.py::test_one", "test_two"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["missing_proof"], [])

    def test_missing_proof_is_named_and_rc_3(self):
        r = self._run(["tests/test_alpha.py"], ["test_one"])
        self.assertEqual(r.returncode, 3)
        out = json.loads(r.stdout)
        self.assertIn("tests/test_alpha.py::TestGroup::test_inner", out["missing_proof"])

    def test_ambiguous_declared_ref_fails_loudly(self):
        r = self._run(["test_shared"], ["tests/test_alpha.py::test_shared"])
        self.assertEqual(r.returncode, 3)
        out = json.loads(r.stdout)
        self.assertEqual(out["declared_errors"][0]["kind"], "ambiguous")
