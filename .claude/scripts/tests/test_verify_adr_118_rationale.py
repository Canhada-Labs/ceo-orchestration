"""Tests for verify-adr-118-rationale.py — PLAN-088 W4.3 / M-27.

5 test cases per plan §4 W4.3 spec:
  1. valid ADR-118 minimal fixture → exit 0 / PASS
  2. synthetic ADR with anti-pattern keyword (`new_capability`) → FAIL
  3. row missing SHA → FAIL
  4. row with surface_delta != "0" → FAIL
  5. row referencing AUTO-99 (not in canonical 13) → FAIL
"""

from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import List, Optional

_THIS = Path(__file__).resolve()
_SCRIPT = _THIS.parent.parent / "verify-adr-118-rationale.py"


def _load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_adr_118_rationale", str(_SCRIPT)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verifier = _load_verifier_module()

CANONICAL_13 = (
    "AUTO-01", "AUTO-02", "AUTO-03", "AUTO-04", "AUTO-05",
    "AUTO-06", "AUTO-07", "AUTO-08", "AUTO-09", "AUTO-10",
    "SEMI-11", "SEMI-12", "SEMI-13",
)


def _minimal_roadmap_yaml() -> str:
    out_lines = ["priority_conversions:"]
    for cid in CANONICAL_13:
        out_lines.append("  - id: %s" % cid)
    return "\n".join(out_lines) + "\n"


def _row(conv: str, primitive: str, sha: str, loc: str, surface: str) -> str:
    return "| %s | %s | %s | %s | %s |" % (conv, primitive, sha, loc, surface)


def _build_adr_text(
    rows: Optional[List[str]] = None,
    inject_anti_pattern: bool = False,
) -> str:
    if rows is None:
        rows = [
            _row(cid, "primitive desc", "ANCESTRAL-PRE-PLAN-084", "100", "0")
            for cid in CANONICAL_13
        ]
    body = (
        "---\n"
        "id: ADR-118\n"
        "title: god-mode AUTO-USABLE\n"
        "status: PROPOSED\n"
        "---\n"
        "\n"
        "# ADR-118 — god-mode AUTO-USABLE\n"
        "\n"
        "## §1 Context\n"
        "stub context.\n"
        "\n"
        "## §2 Decision\n"
        "stub decision.\n"
        "\n"
        "## §3 Rationale\n"
        "\n"
        "| Conversion | Capability primitive | First-shipped SHA | "
        "Trigger-wire LoC | Surface delta |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
        "## §4 Consequences\n"
        "stub.\n"
    )
    if inject_anti_pattern:
        body = body.replace(
            "stub context.",
            "stub context introduces a new_capability primitive here.",
        )
    return body


class _Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="adr118-verify-")
        self.adr_path = Path(self.tmp) / "ADR-118.md"
        self.roadmap_path = Path(self.tmp) / "roadmap.yaml"
        self.roadmap_path.write_text(_minimal_roadmap_yaml(), encoding="utf-8")
        self.last_stdout = ""
        self.last_stderr = ""

    def write_adr(self, text: str) -> None:
        self.adr_path.write_text(text, encoding="utf-8")

    def run(self) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = verifier.run(self.adr_path, self.roadmap_path)
        self.last_stdout = out.getvalue()
        self.last_stderr = err.getvalue()
        return rc

    def cleanup(self) -> None:
        try:
            for p in [self.adr_path, self.roadmap_path]:
                if p.exists():
                    p.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass


class TestVerifyAdr118Rationale(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()

    def tearDown(self) -> None:
        self.fx.cleanup()

    def test_valid_adr_118_passes(self) -> None:
        self.fx.write_adr(_build_adr_text())
        rc = self.fx.run()
        self.assertEqual(rc, 0, "expected exit 0; stderr=%r" % self.fx.last_stderr)
        self.assertIn("PASS", self.fx.last_stdout)

    def test_anti_pattern_keyword_fails(self) -> None:
        self.fx.write_adr(_build_adr_text(inject_anti_pattern=True))
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("anti-pattern keyword", self.fx.last_stderr)

    def test_missing_sha_fails(self) -> None:
        rows: List[str] = []
        for cid in CANONICAL_13:
            sha = "" if cid == "AUTO-05" else "ANCESTRAL-PRE-PLAN-084"
            rows.append(_row(cid, "primitive", sha, "100", "0"))
        self.fx.write_adr(_build_adr_text(rows=rows))
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("AUTO-05", self.fx.last_stderr)
        self.assertIn("SHA", self.fx.last_stderr)

    def test_nonzero_surface_delta_fails(self) -> None:
        rows: List[str] = []
        for cid in CANONICAL_13:
            surface = "1" if cid == "AUTO-07" else "0"
            rows.append(_row(cid, "primitive", "ANCESTRAL-PRE-PLAN-084", "100", surface))
        self.fx.write_adr(_build_adr_text(rows=rows))
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("AUTO-07", self.fx.last_stderr)
        self.assertIn("surface delta", self.fx.last_stderr)

    def test_non_canonical_conversion_id_fails(self) -> None:
        rows: List[str] = []
        for cid in CANONICAL_13[:12]:
            rows.append(_row(cid, "primitive", "ANCESTRAL-PRE-PLAN-084", "100", "0"))
        rows.append(_row("AUTO-99", "rogue", "ANCESTRAL-PRE-PLAN-084", "100", "0"))
        self.fx.write_adr(_build_adr_text(rows=rows))
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("AUTO-99", self.fx.last_stderr)
        self.assertIn("canonical-13", self.fx.last_stderr)
        self.assertIn("missing canonical conversions", self.fx.last_stderr)


if __name__ == "__main__":
    unittest.main()
