"""PLAN-019 DevOps-P2-3 — install-npm.sh emits tarball SHA-256.

Grey-box test: asserts the script content declares the sha256
emission block + manifest side-effects. A live e2e that runs
`npm pack` would require Node/npm on CI and double the runtime for
what is an additive feature over an already-tested path.

Tested invariants (source-level):
- `SHA256SUMS.txt` manifest is appended to (not truncated).
- A single-purpose `<tarball>.sha256` sidecar is emitted alongside
  the tarball so CI can fetch the checksum separately.
- Fallback chain `sha256sum` → `shasum -a 256` → `python3 hashlib`
  is present so the script works on Linux runners (sha256sum),
  macOS (shasum), and minimal containers (python3 always there).
- The emitted manifest line uses the exact format `HASH  FILENAME`
  (two spaces) compatible with `sha256sum -c`.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


_REPO = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO / "scripts" / "install-npm.sh"

# Bootstrap import of TestEnvContext so env isolation holds.
_HOOKS_DIR = _REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


class InstallNpmSha256Test(TestEnvContext):

    def setUp(self):
        super().setUp()
        self.assertTrue(_SCRIPT.exists(), f"{_SCRIPT} missing")
        self.source = _SCRIPT.read_text(encoding="utf-8")

    def test_sha256_header_comment_marks_finding(self):
        # Self-documentation: the block is labeled so future engineers
        # can trace it back to the PLAN-019 remediation.
        self.assertIn("DevOps-P2-3", self.source)

    def test_manifest_file_name(self):
        # The cumulative manifest lives at npm/SHA256SUMS.txt.
        self.assertIn("SHA256SUMS.txt", self.source)

    def test_manifest_is_appended_not_truncated(self):
        # ">> $SHA_MANIFEST" (append) not "> $SHA_MANIFEST" (overwrite).
        # PLAN-023 Phase A: append path is the else branch of the
        # dedup-or-append conditional; the `>>` token still present.
        self.assertIn(">> \"$SHA_MANIFEST\"", self.source)

    def test_manifest_dedup_on_rebuild(self):
        # PLAN-023 Phase A: when the manifest already carries a line
        # for the same tarball filename, install-npm.sh must REPLACE
        # that line in-place rather than append a duplicate. This
        # prevents SHA256SUMS.txt from accumulating stale entries
        # across local rebuilds (previously observed: 51 stale entries
        # before PLAN-025 Batch I reset).
        self.assertIn("grep -qE", self.source)
        self.assertIn("replaced existing line", self.source)
        # awk in-place replacement uses explicit filename-match token.
        self.assertIn('$0 ~ ("  " tb "$")', self.source)

    def test_stale_sidecar_pruned_on_rebuild(self):
        # PLAN-023 Phase A: sidecar files for tarball names OTHER than
        # the current build are removed on each install-npm.sh run, so
        # a RC→GA version bump leaves a clean npm/ directory (previously
        # observed: 1.5.0-rc.1.tgz.sha256 lingered after 1.6.0-rc.1 bump).
        self.assertIn("pruned stale sidecar", self.source)
        self.assertIn("ceo-orchestration-*.tgz.sha256", self.source)

    def test_sidecar_single_file(self):
        # A side-car <tarball>.sha256 is also emitted for CI fetches.
        self.assertIn("$TARBALL_PATH.sha256", self.source)

    def test_fallback_chain_sha256sum_first(self):
        # GNU sha256sum is the preferred tool.
        self.assertIn("command -v sha256sum", self.source)

    def test_fallback_chain_shasum_second(self):
        # BSD shasum -a 256 for macOS without coreutils.
        self.assertIn("command -v shasum", self.source)
        self.assertIn("shasum -a 256", self.source)

    def test_fallback_chain_python_hashlib(self):
        # Last-resort python3 -m hashlib if neither hash tool is
        # available (e.g. minimal Alpine).
        self.assertIn("import hashlib", self.source)

    def test_manifest_line_format_two_spaces(self):
        # sha256sum -c strict format: "HASH  FILENAME" (two spaces).
        self.assertIn('HASH_LINE="${HASH_HEX}  ${TARBALL}"', self.source)

    def test_bash_syntax_valid(self):
        # Defense-in-depth: the script must still be shellcheck-clean
        # (or at least bash-parse-clean). Just bash -n here.
        result = subprocess.run(
            ["bash", "-n", str(_SCRIPT)], capture_output=True
        )
        self.assertEqual(
            result.returncode, 0,
            f"bash -n failed: {result.stderr.decode('utf-8', errors='replace')}"
        )


if __name__ == "__main__":
    unittest.main()
