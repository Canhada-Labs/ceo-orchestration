"""Unit tests for check-sidecar-manifest.py license schema + --check-sbom-sync.

PLAN-112-FOLLOWUP-sbom-third-party-disclosure.

Covers:
  - _validate_licenses: missing licenses key, missing per-package license,
    empty license string, stdlib-only manifest (empty licenses OK).
  - _pkg_name / _declared_python_packages: version-pin stripping.
  - _parse_sbom_section_b_packages: anchor-bounded backtick parsing.
  - check_sbom_sync: positive (all present), negative (declared-not-listed),
    missing/empty Section-B anchor block.

The module under test loads functions but check_sbom_sync() reads module-level
_REPO_ROOT / _SIDECARS_ROOT / _SBOM_PATH (resolved from the script's own
location). To exercise it against a temp tree we monkeypatch those constants.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "check-sidecar-manifest.py"
_spec = importlib.util.spec_from_file_location("check_sidecar_manifest", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _base_manifest(tier="A", cls="C5", pkgs=None, licenses=None):
    pkgs = ["hypothesis==6.100.0"] if pkgs is None else pkgs
    licenses = {"hypothesis": "MPL-2.0"} if licenses is None else licenses
    return {
        "sidecar": {"name": "x", "capability_class": cls, "version": "1.0.0", "default_tier": tier},
        "isolation": {
            "core_paths_blocked": [".claude/hooks/"],
            "core_paths_allowlisted_workflow_invokers": [".github/workflows/coverage.yml"],
            "import_roots": ["hypothesis"],
            "allowed_workflow_invocation_patterns": ["^python3? x"],
            "boundary_test": "boundary_test.py",
        },
        "dependencies": {"python": pkgs, "system": [], "licenses": licenses},
        "governance": {
            "kill_switch_env": "CEO_SIDECAR_HYPOTHESIS_ENABLED",
            "default_state": "on",
            "activation_predicate": "always-true",
            "enable_value": "1",
            "disable_value": "0",
            "explicit_opt_in_required": False,
            "authorizing_adr": "ADR-131",
            "cost_envelope": {"per_invocation_tokens": 0, "daily_burn_cap": 0, "enforcement": "disabled"},
        },
        "install": {"script": "install.sh", "hw_class_check": "none"},
    }


class TestPkgName(unittest.TestCase):
    def test_strip_pins(self):
        self.assertEqual(mod._pkg_name("cryptography>=42.0,<44.0"), "cryptography")
        self.assertEqual(mod._pkg_name("sentence-transformers==2.5.1"), "sentence-transformers")
        self.assertEqual(mod._pkg_name("lightrag==0.1.0"), "lightrag")
        self.assertEqual(mod._pkg_name("  hypothesis == 6.100.0 "), "hypothesis")

    def test_declared_packages(self):
        data = _base_manifest(pkgs=["chromadb==0.4.24", "lightrag==0.1.0"])
        self.assertEqual(mod._declared_python_packages(data), ["chromadb", "lightrag"])

    def test_declared_empty(self):
        data = _base_manifest(pkgs=[], licenses={})
        self.assertEqual(mod._declared_python_packages(data), [])


class TestValidateLicenses(unittest.TestCase):
    def _viol(self, data):
        v = []
        mod._validate_licenses(data, Path(mod._REPO_ROOT / "x.json"), v)
        return v

    def test_ok(self):
        self.assertEqual(self._viol(_base_manifest()), [])

    def test_stdlib_only_empty_licenses_ok(self):
        self.assertEqual(self._viol(_base_manifest(pkgs=[], licenses={})), [])

    def test_missing_licenses_key(self):
        d = _base_manifest()
        del d["dependencies"]["licenses"]
        v = self._viol(d)
        self.assertTrue(any("dependencies.licenses missing" in x for x in v))

    def test_missing_per_package_license(self):
        d = _base_manifest(pkgs=["hypothesis==6.100.0", "jsonschema==4.21.1"], licenses={"hypothesis": "MPL-2.0"})
        v = self._viol(d)
        self.assertTrue(any("jsonschema" in x for x in v))

    def test_empty_license_string(self):
        d = _base_manifest(licenses={"hypothesis": "  "})
        v = self._viol(d)
        self.assertTrue(any("hypothesis" in x for x in v))

    def test_licenses_not_object(self):
        d = _base_manifest()
        d["dependencies"]["licenses"] = ["MPL-2.0"]
        v = self._viol(d)
        self.assertTrue(any("must be an object" in x for x in v))


class TestSbomParse(unittest.TestCase):
    def test_anchor_bounded(self):
        text = (
            "preamble `notapkg` outside anchors\n"
            "<!-- SBOM-SECTION-B:BEGIN -->\n"
            "| Package | x |\n|---|---|\n"
            "| `cryptography` | a |\n"
            "| `chromadb` | b |\n"
            "<!-- SBOM-SECTION-B:END -->\n"
            "trailer `alsonot` outside\n"
        )
        pkgs = mod._parse_sbom_section_b_packages(text)
        self.assertEqual(pkgs, {"cryptography", "chromadb"})

    def test_no_anchors_returns_empty(self):
        self.assertEqual(mod._parse_sbom_section_b_packages("| `x` |"), set())


class TestCheckSbomSync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sbom-sync-test-"))
        self.sidecars = self.tmp / ".claude" / "sidecars"
        (self.sidecars / "c5-dev-tools" / "hypothesis").mkdir(parents=True)
        self._orig = (mod._REPO_ROOT, mod._SIDECARS_ROOT, mod._SBOM_PATH)
        mod._REPO_ROOT = self.tmp
        mod._SIDECARS_ROOT = self.sidecars
        mod._SBOM_PATH = self.tmp / "SBOM.md"

    def tearDown(self):
        mod._REPO_ROOT, mod._SIDECARS_ROOT, mod._SBOM_PATH = self._orig
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_manifest(self, pkgs, licenses):
        d = _base_manifest(pkgs=pkgs, licenses=licenses)
        p = self.sidecars / "c5-dev-tools" / "hypothesis" / "manifest.json"
        p.write_text(json.dumps(d, indent=2))

    def _write_sbom(self, listed):
        rows = "\n".join(f"| `{p}` | x |" for p in listed)
        self.tmp.joinpath("SBOM.md").write_text(
            "x\n<!-- SBOM-SECTION-B:BEGIN -->\n| Package | x |\n|---|---|\n"
            f"{rows}\n<!-- SBOM-SECTION-B:END -->\n"
        )

    def test_all_present_ok(self):
        self._write_manifest(["hypothesis==6.100.0", "jsonschema==4.21.1"], {"hypothesis": "MPL-2.0", "jsonschema": "MIT"})
        self._write_sbom(["hypothesis", "jsonschema"])
        self.assertEqual(mod.check_sbom_sync(), 0)

    def test_declared_not_listed_fails(self):
        self._write_manifest(["hypothesis==6.100.0", "jsonschema==4.21.1"], {"hypothesis": "MPL-2.0", "jsonschema": "MIT"})
        self._write_sbom(["hypothesis"])  # jsonschema missing
        self.assertEqual(mod.check_sbom_sync(), 1)

    def test_missing_anchor_block_with_decls_fails(self):
        self._write_manifest(["hypothesis==6.100.0"], {"hypothesis": "MPL-2.0"})
        self.tmp.joinpath("SBOM.md").write_text("no anchors here, plain text\n")
        self.assertEqual(mod.check_sbom_sync(), 1)

    def test_missing_sbom_file_fails(self):
        self._write_manifest(["hypothesis==6.100.0"], {"hypothesis": "MPL-2.0"})
        # do not write SBOM.md
        self.assertEqual(mod.check_sbom_sync(), 1)


if __name__ == "__main__":
    unittest.main()
