"""Unit tests for check_threat_model_coverage.py — PLAN-013 Phase C.5.

Subclasses `TestEnvContext` per CLAUDE.md §5 + PLAN-013 consensus §S11.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = SCRIPT_ROOT / "scripts" / "check_threat_model_coverage.py"


def _git_init(tmpdir: Path) -> None:
    (tmpdir / ".git").mkdir(exist_ok=True)


def _write_adr(
    tmpdir: Path,
    adr_id: str,
    slug: str,
    content: str,
) -> Path:
    adr_dir = tmpdir / ".claude" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    path = adr_dir / f"ADR-{adr_id}-{slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_threat_model(tmpdir: Path, content: str) -> Path:
    docs = tmpdir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    path = docs / "threat-model.md"
    path.write_text(content, encoding="utf-8")
    return path


def _run(tmpdir: Path, json_out: bool = False):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(tmpdir),
    ]
    if json_out:
        cmd.append("--json")
    return subprocess.run(cmd, capture_output=True, text=True)


class TestThreatModelCoverage(TestEnvContext):
    def _setup(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)
        _git_init(self.project_dir)

    def test_covered_security_adr_passes(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "050",
            "auth-middleware",
            "# ADR-050\n\nThis decision impacts authentication and credential rotation.\n",
        )
        _write_threat_model(
            self.project_dir,
            "# Threat model\n\nSee ADR-050 threat row.\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_uncovered_security_adr_fails(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "051",
            "credential-vault",
            "# ADR-051\n\nCredential rotation lifecycle.\n",
        )
        _write_threat_model(
            self.project_dir,
            "# Threat model\n\nOther ADRs covered.\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING", result.stdout)

    def test_non_security_adr_ignored(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "060",
            "directory-layout",
            "# ADR-060\n\nPackage directory naming choice. "
            "security-scope: N/A\n",
        )
        _write_threat_model(
            self.project_dir,
            "# Threat model\n\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("skip", result.stdout)

    def test_opt_out_marker_bypasses_security_keywords(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "061",
            "observability",
            "# ADR-061\n\nThis ADR discusses audit logging but is not a "
            "security decision. security-scope: N/A\n",
        )
        _write_threat_model(
            self.project_dir,
            "# Threat model\n\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 0)

    def test_mixed_pass_and_fail_reports_all(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "070",
            "auth-first",
            "# ADR-070\n\nauthentication scope.\n",
        )
        _write_adr(
            self.project_dir,
            "071",
            "auth-second",
            "# ADR-071\n\nauthorization scope.\n",
        )
        _write_threat_model(
            self.project_dir,
            "# Threat model\n\nADR-070 covered.\n",
        )
        result = _run(self.project_dir, json_out=True)
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        ok_map = {r["adr"]: r["ok"] for r in data["rows"]}
        self.assertTrue(ok_map["ADR-070"])
        self.assertFalse(ok_map["ADR-071"])

    def test_empty_adr_dir_returns_zero(self) -> None:
        self._setup()
        (self.project_dir / ".claude" / "adr").mkdir(parents=True)
        _write_threat_model(self.project_dir, "# empty\n")
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 0)

    def test_missing_adr_dir_returns_2(self) -> None:
        self._setup()
        _write_threat_model(self.project_dir, "# t\n")
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("adr dir not found", result.stderr)

    def test_missing_threat_model_returns_2(self) -> None:
        self._setup()
        (self.project_dir / ".claude" / "adr").mkdir(parents=True)
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("threat model not found", result.stderr)

    def test_json_output_contains_required_keys(self) -> None:
        self._setup()
        _write_adr(
            self.project_dir,
            "080",
            "sample",
            "# ADR-080\n\nauth scope.\n",
        )
        _write_threat_model(
            self.project_dir,
            "# t\n\nADR-080 cited.\n",
        )
        result = _run(self.project_dir, json_out=True)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("rows", data)
        self.assertIn("missing", data)
        self.assertFalse(data["missing"])
        self.assertEqual(len(data["rows"]), 1)
        row = data["rows"][0]
        self.assertIn("adr", row)
        self.assertIn("path", row)
        self.assertIn("security_scoped", row)
        self.assertIn("in_threat_model", row)
        self.assertIn("ok", row)

    def test_multiple_security_keywords_tripped(self) -> None:
        self._setup()
        kw_samples = [
            ("sentinel-flow", "sentinel enforcement"),
            ("breaker-contract", "breaker state machine"),
            ("output-safety", "output safety pipeline"),
            ("rate-limiter", "rate-limit bucket"),
            ("tamper-check", "tamper detection"),
        ]
        for i, (slug, body) in enumerate(kw_samples, start=90):
            _write_adr(
                self.project_dir,
                str(i),
                slug,
                f"# ADR-{i:03d}\n\n{body} — feature.\n",
            )
        refs = "".join(f"ADR-{i:03d} " for i in range(90, 95))
        _write_threat_model(
            self.project_dir,
            f"# Threat model\n\n{refs}\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_adr_directory_detects_corpus(self) -> None:
        """Smoke test against the real repo."""
        real_root = Path(__file__).resolve().parents[3]
        adr_dir = real_root / ".claude" / "adr"
        threat_model = real_root / "docs" / "threat-model.md"
        if not adr_dir.is_dir() or not threat_model.is_file():
            self.skipTest("real corpus not available")
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--adr-dir",
            str(adr_dir),
            "--threat-model",
            str(threat_model),
            "--repo-root",
            str(real_root),
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("rows", data)
        self.assertGreater(len(data["rows"]), 10)


if __name__ == "__main__":
    import unittest
    unittest.main()
