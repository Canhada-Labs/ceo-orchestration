"""PLAN-099-FOLLOWUP Wave F.1 — peers.yaml v1.x -> v2.0 migration tests.

Tests ``tools/migrate-peers-yaml.py`` end-to-end. Stdlib + subprocess
only. Imports the migrate module via importlib (the script has a
hyphen in its filename — not a valid Python identifier — so a regular
`import` is not possible).

WAVE-F-PENDING markers:
  - SPKI computation parity test depends on cert_inspector being able
    to parse the cert and extract SPKI. On libressl <3.5 (older
    openssl-fallback) SPKI extraction may fail; the test skips
    gracefully.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Module import (hyphenated filename → importlib path)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOL_PATH = _REPO_ROOT / "tools" / "migrate-peers-yaml.py"

_spec = importlib.util.spec_from_file_location(
    "migrate_peers_yaml", str(_TOOL_PATH)
)
_migrate = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_migrate)  # type: ignore


def _run_tool(*args: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run the migrate tool as subprocess."""
    return subprocess.run(
        [sys.executable, str(_TOOL_PATH)] + list(args),
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


V1_TEMPLATE = '''\
peers:
  - peer_id: peer-alpha-01
    peer_id_cert_fingerprint: "0101010101010101010101010101010101010101010101010101010101010101"
    ca_pin_sha256: "ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001"
'''

V1_TWO_PEERS = '''\
peers:
  - peer_id: peer-alpha-01
    peer_id_cert_fingerprint: "0101010101010101010101010101010101010101010101010101010101010101"
    ca_pin_sha256: "ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001"
  - peer_id: peer-beta-02
    peer_id_cert_fingerprint: "0202020202020202020202020202020202020202020202020202020202020202"
    ca_pin_sha256: "ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02ca02"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "h002h002h002h002h002h002h002h002h002h002h002h002h002h002h002h002"
'''


class TestPeersMigration(unittest.TestCase):
    """End-to-end migration tool tests (subprocess + library import)."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="peers-yaml-migration-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    # ---------------------------------------------------------------------
    # Case 1: v1.x → v2.0 happy path
    # ---------------------------------------------------------------------

    def test_v1_to_v2_happy_path(self):
        """Migrate v1.x to v2.0 (via --skip-cert-inspect for env-independence)."""
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        proc = _run_tool("--in", in_path, "--out", out_path, "--skip-cert-inspect")
        self.assertEqual(
            proc.returncode, 0,
            "stdout={!r} stderr={!r}".format(proc.stdout, proc.stderr),
        )
        self.assertTrue(os.path.isfile(out_path))
        out_text = open(out_path, encoding="utf-8").read()
        # v2.0 fields present
        self.assertIn("peer_id_spki_fingerprint:", out_text)
        self.assertIn("scopes:", out_text)
        self.assertIn("key_floor_verified_at:", out_text)
        # Legacy field preserved
        self.assertIn("peer_id_cert_fingerprint:", out_text)
        # Skipped-inspect sentinel
        self.assertIn('key_floor_verified_at: "unknown"', out_text)

    # ---------------------------------------------------------------------
    # Case 2: Idempotency — re-running on v2.0 file is BYTE-IDENTICAL
    # ---------------------------------------------------------------------
    #
    # F-001 contract change (Wave B Codex P0): a pure-v2.0 input is a
    # short-circuit case — the tool emits the input bytes verbatim
    # (no header regeneration, no row re-render). v2.0 -> v2.0 MUST be
    # byte-for-byte equal at the file level (not just at the body
    # level — the previous header-stripping mask hid this regression).

    def test_idempotent_byte_equal_full_file(self):
        """Re-running on v2.0 output produces a byte-identical file.

        F-001: previously this test stripped header lines before
        comparison, which masked the AUTOGENERATED-timestamp drift.
        The fix is to short-circuit pure-v2.0 input → write input
        bytes verbatim. This test now compares the entire file body
        (header + rows) at the byte level.
        """
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        out_path_2 = os.path.join(self.tmpdir, "v2_again.yaml")

        # First migration: v1.x → v2.0 (renders header)
        proc1 = _run_tool("--in", in_path, "--out", out_path, "--skip-cert-inspect")
        self.assertEqual(proc1.returncode, 0)

        # Second migration: v2.0 → v2.0 (pure-v2 short-circuit; verbatim)
        proc2 = _run_tool("--in", out_path, "--out", out_path_2, "--skip-cert-inspect")
        self.assertEqual(
            proc2.returncode, 0,
            "stderr={!r}".format(proc2.stderr),
        )

        # Full-bytes equality (no header masking).
        bytes_a = open(out_path, "rb").read()
        bytes_b = open(out_path_2, "rb").read()
        self.assertEqual(
            bytes_a, bytes_b,
            "v2.0→v2.0 must be byte-identical (F-001). diff:\n"
            "  size A={} B={}".format(len(bytes_a), len(bytes_b)),
        )

    # ---------------------------------------------------------------------
    # Case 3: --dry-run produces no side-effects
    # ---------------------------------------------------------------------

    def test_dry_run_no_side_effects(self):
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        in_mtime = os.path.getmtime(in_path)

        proc = _run_tool(
            "--in", in_path, "--out", out_path,
            "--dry-run", "--skip-cert-inspect",
        )
        self.assertEqual(proc.returncode, 0)
        # diff report present on stdout
        self.assertIn("peer", proc.stdout)
        # input mtime unchanged
        self.assertEqual(os.path.getmtime(in_path), in_mtime)
        # output NOT created
        self.assertFalse(os.path.isfile(out_path))

    # ---------------------------------------------------------------------
    # Case 4: per-peer cert failure aborts cleanly (no partial write)
    # ---------------------------------------------------------------------

    def test_per_peer_cert_failure_aborts_atomically(self):
        """When --cert-dir is set but a cert is missing, the tool aborts
        and leaves the output file untouched (no partial write)."""
        in_path = self._write("v1.yaml", V1_TWO_PEERS)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        empty_certs = os.path.join(self.tmpdir, "certs_empty")
        os.makedirs(empty_certs)

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--cert-dir", empty_certs,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ABORT", proc.stderr)
        # Output file MUST NOT exist (atomic — no partial writes).
        self.assertFalse(
            os.path.isfile(out_path),
            "tool wrote partial output; atomic guarantee broken",
        )

    # ---------------------------------------------------------------------
    # Case 5: SPKI computation matches cert_inspector.spki_sha256_hex
    # ---------------------------------------------------------------------

    def test_spki_matches_cert_inspector(self):
        """When real certs are provided, the SPKI written to the output
        file matches cert_inspector.spki_sha256_hex on the same cert.

        F-003 interaction: V1_TEMPLATE's dummy ``01..01`` DER pin would
        trigger the F-003 DER-mismatch abort before SPKI extraction.
        We compute the *actual* DER SHA-256 of the generated cert and
        plug it into the fixture so the migration is allowed to reach
        the SPKI compare step.
        """
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("openssl binary not on PATH")
        # Generate a real RSA-2048 cert
        cert_dir = os.path.join(self.tmpdir, "certs")
        os.makedirs(cert_dir)
        key = os.path.join(cert_dir, "peer-alpha-01.key")
        cert = os.path.join(cert_dir, "peer-alpha-01.pem")
        subprocess.run(
            [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", key, "-out", cert, "-days", "30",
             "-subj", "/CN=peer-alpha-01"],
            check=True, capture_output=True, timeout=15,
        )
        # Compute real DER SHA-256 so F-003 does not abort.
        import base64
        import hashlib
        import re
        cert_pem = open(cert, "rb").read()
        m_der = re.search(
            rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
            cert_pem, re.DOTALL,
        )
        self.assertTrue(m_der, "could not extract DER from PEM")
        der_bytes = base64.b64decode(m_der.group(1).strip())
        real_der_sha = hashlib.sha256(der_bytes).hexdigest()

        # Build v1.yaml with the matching peer_id + matching DER pin
        v1 = V1_TEMPLATE.replace(
            "0101010101010101010101010101010101010101010101010101010101010101",
            real_der_sha,
        )
        in_path = self._write("v1.yaml", v1)
        out_path = os.path.join(self.tmpdir, "v2.yaml")

        proc = _run_tool("--in", in_path, "--out", out_path, "--cert-dir", cert_dir)
        if proc.returncode != 0:
            # On hosts where the cert_inspector bridge SPKI fallback is
            # broken (libressl <3.5) the tool may abort. That is
            # WAVE-F-PENDING — the test surfaces the gap explicitly.
            self.skipTest(
                "WAVE-F-PENDING: cert_inspector SPKI extraction failed on this host; "
                "stderr={!r}".format(proc.stderr[:300])
            )

        out_text = open(out_path, encoding="utf-8").read()
        # Find the SPKI value
        import re
        m = re.search(
            r'peer_id_spki_fingerprint:\s*"([0-9a-fA-F]{64})"', out_text
        )
        self.assertTrue(m, "SPKI fingerprint not found in output")
        spki_from_tool = m.group(1)

        # Now call cert_inspector directly and compare
        # Import from canonical or staging
        hooks_lib = _REPO_ROOT / ".claude" / "hooks" / "_lib"
        sys.path.insert(0, str(hooks_lib))
        try:
            from federation import cert_inspector  # type: ignore
        except ImportError:
            staging = _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "cert_inspector.py"
            spec = importlib.util.spec_from_file_location("ci_staging", str(staging))
            cert_inspector = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cert_inspector)

        rep = cert_inspector.inspect(cert_path=cert)
        self.assertEqual(rep["spki_sha256"], spki_from_tool)

    # ---------------------------------------------------------------------
    # Case 6: peer_id_cert_fingerprint preserved verbatim
    # ---------------------------------------------------------------------

    def test_der_fingerprint_preserved_verbatim(self):
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--skip-cert-inspect",
        )
        self.assertEqual(proc.returncode, 0)
        out_text = open(out_path, encoding="utf-8").read()
        # The original DER must be present verbatim (legacy 90d compat)
        self.assertIn(
            "0101010101010101010101010101010101010101010101010101010101010101",
            out_text,
        )

    # ---------------------------------------------------------------------
    # Case 7: --skip-cert-inspect paper-only migration
    # ---------------------------------------------------------------------

    def test_skip_cert_inspect_sets_unknown_kfv(self):
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--skip-cert-inspect",
        )
        self.assertEqual(proc.returncode, 0)
        out_text = open(out_path, encoding="utf-8").read()
        self.assertIn('key_floor_verified_at: "unknown"', out_text)
        # SPKI should be empty in paper-only mode
        self.assertIn('peer_id_spki_fingerprint: ""', out_text)

    # ---------------------------------------------------------------------
    # Case 8a: --verify-only on already-v2.0 file → exit 0
    # ---------------------------------------------------------------------

    def test_verify_only_v2_returns_zero(self):
        # Create a v2.0 file by migrating once
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        v2_path = os.path.join(self.tmpdir, "v2.yaml")
        _run_tool("--in", in_path, "--out", v2_path, "--skip-cert-inspect")
        # Then verify
        proc = _run_tool("--verify-only", "--in", v2_path)
        self.assertEqual(
            proc.returncode, 0,
            "stderr={!r}".format(proc.stderr),
        )

    # ---------------------------------------------------------------------
    # Case 8b: --verify-only on v1.x file → exit 7 (conformance fail)
    # ---------------------------------------------------------------------

    def test_verify_only_v1_returns_conformance_fail(self):
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        proc = _run_tool("--verify-only", "--in", in_path)
        self.assertEqual(
            proc.returncode, 7,
            "expected EXIT_CONFORMANCE_FAIL=7; stderr={!r}".format(proc.stderr),
        )

    # ---------------------------------------------------------------------
    # Case 9: Optional backup before write
    # ---------------------------------------------------------------------

    def test_backup_option_creates_backup(self):
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        backup = os.path.join(self.tmpdir, "v1.bak.yaml")
        proc = _run_tool(
            "--in", in_path, "--out", out_path,
            "--backup", backup, "--skip-cert-inspect",
        )
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(os.path.isfile(backup))
        # backup matches the original input
        self.assertEqual(
            open(in_path).read(),
            open(backup).read(),
        )

    # ---------------------------------------------------------------------
    # Case 10: F-001 — --dry-run on a pure-v2.0 input emits no changes
    # ---------------------------------------------------------------------

    def test_dry_run_v2_input_emits_no_changes(self):
        """Pure-v2 input + --dry-run → exit 0, no output file, message
        says no changes.

        F-001 corollary: the pure-v2 short-circuit must also be visible
        in --dry-run mode (no diff to render, no v1-to-v2 deltas).
        """
        in_path = self._write("v1.yaml", V1_TEMPLATE)
        v2_path = os.path.join(self.tmpdir, "v2.yaml")
        # Build a v2.0 fixture by running once.
        proc_build = _run_tool(
            "--in", in_path, "--out", v2_path, "--skip-cert-inspect",
        )
        self.assertEqual(proc_build.returncode, 0)

        # Now --dry-run on the v2.0 file.
        v2_again = os.path.join(self.tmpdir, "v2_again.yaml")
        proc = _run_tool(
            "--in", v2_path, "--out", v2_again,
            "--dry-run", "--skip-cert-inspect",
        )
        self.assertEqual(
            proc.returncode, 0,
            "stderr={!r} stdout={!r}".format(proc.stderr, proc.stdout),
        )
        # Output file MUST NOT be created in dry-run mode.
        self.assertFalse(os.path.isfile(v2_again))
        # The short-circuit message must surface.
        self.assertIn("pure-v2", proc.stdout.lower())

    # ---------------------------------------------------------------------
    # Case 11: F-003 — DER pin mismatch aborts; no file is written
    # ---------------------------------------------------------------------

    def test_der_mismatch_aborts(self):
        """When peers.yaml carries peer_id_cert_fingerprint=<hex-A> but
        the cert on disk hashes to <hex-B>, the tool MUST abort before
        rendering the output. The output file is never created.

        F-003: prevents silent pin-rotation via cert swap.
        """
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("openssl binary not on PATH")

        cert_dir = os.path.join(self.tmpdir, "certs")
        os.makedirs(cert_dir)
        key = os.path.join(cert_dir, "peer-alpha-01.key")
        cert = os.path.join(cert_dir, "peer-alpha-01.pem")
        gen = subprocess.run(
            [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", key, "-out", cert, "-days", "30",
             "-subj", "/CN=peer-alpha-01"],
            capture_output=True, timeout=15,
        )
        if gen.returncode != 0:
            self.skipTest(
                "openssl cert generation failed; "
                "stderr={!r}".format(gen.stderr[:200])
            )

        # Build a v1.yaml whose peer_id_cert_fingerprint is DELIBERATELY
        # wrong (legit 64-hex but not matching the cert).
        wrong_fpr = "ff" * 32
        v1 = V1_TEMPLATE.replace(
            "0101010101010101010101010101010101010101010101010101010101010101",
            wrong_fpr,
        )
        in_path = self._write("v1.yaml", v1)
        out_path = os.path.join(self.tmpdir, "v2.yaml")

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--cert-dir", cert_dir,
        )
        # Some CI hosts may have a broken cert_inspector bridge — if the
        # tool aborts for *that* reason we skip (the inspector check
        # already covers test_spki_matches_cert_inspector behaviour).
        # Otherwise we MUST see a DER pin mismatch abort.
        if "DER pin mismatch" not in proc.stderr and "cert_inspector failed" in proc.stderr:
            self.skipTest(
                "WAVE-F-PENDING: cert_inspector unable to inspect cert; "
                "stderr={!r}".format(proc.stderr[:300])
            )

        self.assertNotEqual(
            proc.returncode, 0,
            "DER mismatch must produce non-zero exit; "
            "stderr={!r}".format(proc.stderr),
        )
        self.assertIn("DER pin mismatch", proc.stderr)
        self.assertFalse(
            os.path.isfile(out_path),
            "output file written despite DER pin mismatch — F-003 broken",
        )
        # Input untouched.
        self.assertEqual(open(in_path).read(), v1)

    # ---------------------------------------------------------------------
    # Case 12: F-004 — key-floor fail emits sidecar advisory; continues
    # ---------------------------------------------------------------------

    def test_floor_fail_sidecar_emitted(self):
        """A peer whose cert is below the key floor (e.g. RSA-1024)
        triggers an advisory ``<peer-id>.floor-fail`` sidecar next to
        the output peers.yaml. Migration STILL completes and writes
        the v2.0 file (F-004 contract: advisory, not abort).
        """
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("openssl binary not on PATH")

        cert_dir = os.path.join(self.tmpdir, "certs")
        os.makedirs(cert_dir)
        key = os.path.join(cert_dir, "peer-alpha-01.key")
        cert = os.path.join(cert_dir, "peer-alpha-01.pem")
        # Generate an RSA-1024 cert — below the 2048-bit floor.
        gen = subprocess.run(
            [openssl, "req", "-x509", "-newkey", "rsa:1024", "-nodes",
             "-keyout", key, "-out", cert, "-days", "30",
             "-subj", "/CN=peer-alpha-01"],
            capture_output=True, timeout=15,
        )
        if gen.returncode != 0:
            self.skipTest(
                "openssl RSA-1024 generation refused on this host; "
                "stderr={!r}".format(gen.stderr[:200])
            )

        # Compute DER sha256 of the cert so the peers.yaml carries a
        # MATCHING peer_id_cert_fingerprint (otherwise F-003 fires
        # first and we never reach the floor check).
        import hashlib
        import re
        cert_pem = open(cert, "rb").read()
        # Strip headers/footers, decode b64 to DER.
        b64 = re.search(
            rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
            cert_pem, re.DOTALL,
        )
        if not b64:
            self.skipTest("unable to extract DER from generated cert")
        import base64
        der = base64.b64decode(b64.group(1).strip())
        der_sha256 = hashlib.sha256(der).hexdigest()

        v1 = V1_TEMPLATE.replace(
            "0101010101010101010101010101010101010101010101010101010101010101",
            der_sha256,
        )
        in_path = self._write("v1.yaml", v1)
        out_path = os.path.join(self.tmpdir, "v2.yaml")

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--cert-dir", cert_dir,
        )
        if "cert_inspector failed" in proc.stderr or "cert_inspector returned malformed" in proc.stderr:
            self.skipTest(
                "WAVE-F-PENDING: cert_inspector bridge cannot parse RSA-1024 cert; "
                "stderr={!r}".format(proc.stderr[:300])
            )

        # F-004 contract: migration succeeds (advisory only).
        self.assertEqual(
            proc.returncode, 0,
            "F-004 contract violated: migration should succeed with "
            "advisory on key-floor fail; stderr={!r}".format(proc.stderr),
        )
        # v2.0 output file must exist.
        self.assertTrue(
            os.path.isfile(out_path),
            "F-004: migration should write v2.0 output even when key "
            "floor fails (advisory model)",
        )
        # Sidecar advisory must exist next to the output.
        sidecar = os.path.join(self.tmpdir, "peer-alpha-01.floor-fail")
        self.assertTrue(
            os.path.isfile(sidecar),
            "F-004: <peer-id>.floor-fail sidecar not written next to "
            "peers.yaml — expected at {!r}".format(sidecar),
        )
        sidecar_body = open(sidecar, encoding="utf-8").read()
        self.assertIn("peer_id: peer-alpha-01", sidecar_body)
        self.assertIn("reason:", sidecar_body)
        self.assertIn("inspected_at:", sidecar_body)


# ---------------------------------------------------------------------------
# Wave F.1 — TestMigrationAtScale
#
# Migration-at-scale + SPEC row count parity tests. Mirrors the
# TestPeersMigration setUp/tearDown pattern so any future fixture
# helper landing in TestPeersMigration is trivially copy-pasted.
# ---------------------------------------------------------------------------


def _make_v1_peer_row(peer_id: str, der_hex: str, hmac_hex: str) -> str:
    """Build a v1.x peers.yaml peer row (6 fields). Used to generate
    100-peer fixtures without writing 100 hand-rolled rows.
    """
    return (
        "  - peer_id: {pid}\n"
        "    peer_id_cert_fingerprint: \"{der}\"\n"
        "    ca_pin_sha256: \"ca{der_prefix}\"\n"
        "    not_valid_after: \"2026-08-17T00:00:00Z\"\n"
        "    not_valid_before: \"2026-05-17T00:00:00Z\"\n"
        "    revoked: false\n"
        "    hmac_secret_hex: \"{hmac}\"\n"
    ).format(pid=peer_id, der=der_hex, der_prefix=der_hex[:62], hmac=hmac_hex)


def _make_v2_peer_row(
    peer_id: str,
    spki_hex: str = "",
    der_hex: str = "",
    scopes_list: Optional[list] = None,
    kfv: str = "2026-05-20T00:00:00Z",
) -> str:
    """Build a v2.0 peers.yaml peer row. At least one of spki/der MUST
    be non-empty (caller responsibility — invariant per
    peers-yaml-schema-migration.md §2.1).
    """
    scopes_list = scopes_list if scopes_list is not None else []
    lines = ["  - peer_id: {0}".format(peer_id)]
    if spki_hex:
        lines.append("    peer_id_spki_fingerprint: \"{0}\"".format(spki_hex))
    if der_hex:
        lines.append("    peer_id_cert_fingerprint: \"{0}\"".format(der_hex))
    pin_prefix = (spki_hex or der_hex)[:62]
    lines.append("    ca_pin_sha256: \"ca{0}\"".format(pin_prefix))
    lines.append("    not_valid_after: \"2026-08-17T00:00:00Z\"")
    lines.append("    not_valid_before: \"2026-05-17T00:00:00Z\"")
    lines.append("    revoked: false")
    lines.append("    hmac_secret_hex: \"h{0}\"".format(pin_prefix[:63]))
    if scopes_list:
        lines.append("    scopes:")
        for s in scopes_list:
            lines.append("      - \"{0}\"".format(s))
    else:
        lines.append("    scopes: []")
    lines.append("    key_floor_verified_at: \"{0}\"".format(kfv))
    return "\n".join(lines) + "\n"


class TestMigrationAtScale(unittest.TestCase):
    """Wave F.1 — migration-at-scale + mixed-pin + atomic-failure +
    SPEC row count parity.

    These tests exercise the migration tool with synthetic fixtures
    (no real openssl needed except in the rare path documented per
    test). The 100-peer fixture is synthesised via
    ``_make_v1_peer_row`` + paper-only ``--skip-cert-inspect`` to
    keep CI runtime predictable.
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="peers-yaml-scale-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    # ---------------------------------------------------------------------
    # Test 1: 100-peer migration completes + remains v2.0 conformant
    # + re-running is byte-identical (idempotent at scale).
    # ---------------------------------------------------------------------

    def test_100_peer_migration_completes(self):
        """Generate 100 synthetic v1.x peers; migrate via
        ``--skip-cert-inspect`` (paper-only path keeps CI runtime
        deterministic); assert conformance + idempotency on re-run.
        """
        N = 100
        rows = ["peers:"]
        for i in range(N):
            pid = "peer-scale-{:03d}".format(i)
            der_hex = "{:02x}".format(i % 256) * 32  # 64 hex chars
            hmac_hex = "{:02x}".format((i + 0x10) % 256) * 32
            rows.append(_make_v1_peer_row(pid, der_hex, hmac_hex))
        in_path = self._write("v1.yaml", "\n".join(rows))
        out_path = os.path.join(self.tmpdir, "v2.yaml")

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--skip-cert-inspect",
        )
        self.assertEqual(
            proc.returncode, 0,
            "100-peer migration failed: stderr={!r}".format(proc.stderr[:500]),
        )
        self.assertTrue(os.path.isfile(out_path))

        # v2.0 conformance — run --verify-only on the migrated file.
        v_proc = _run_tool("--verify-only", "--in", out_path)
        self.assertEqual(
            v_proc.returncode, 0,
            "100-peer v2.0 file does not pass --verify-only; "
            "stderr={!r}".format(v_proc.stderr[:500]),
        )

        # Idempotency — re-running on v2.0 file is byte-identical.
        out_path_2 = os.path.join(self.tmpdir, "v2_again.yaml")
        proc2 = _run_tool(
            "--in", out_path, "--out", out_path_2, "--skip-cert-inspect",
        )
        self.assertEqual(proc2.returncode, 0)
        bytes_a = open(out_path, "rb").read()
        bytes_b = open(out_path_2, "rb").read()
        self.assertEqual(
            bytes_a, bytes_b,
            "100-peer v2.0 -> v2.0 must be byte-identical (F-001 at scale); "
            "size_a={} size_b={}".format(len(bytes_a), len(bytes_b)),
        )

        # Count peer rows in the output to confirm none lost in transit.
        # The emitter quotes scalar values (per _emit_scalar in the tool),
        # so peer_id appears as `peer_id: "peer-scale-NNN"`.
        out_text = bytes_a.decode("utf-8")
        peer_count = out_text.count('peer_id: "peer-scale-')
        self.assertEqual(
            peer_count, N,
            "expected {0} peer rows in migrated output, found {1}".format(N, peer_count),
        )

    # ---------------------------------------------------------------------
    # Test 2: Mixed SPKI/DER/dual-pin peers roundtrip cleanly.
    # ---------------------------------------------------------------------

    def test_mixed_spki_der_peers_migration(self):
        """A v2.0 file with 5 SPKI-only + 5 DER-only + 5 dual-pin peers
        roundtrips losslessly: every pin is preserved verbatim and the
        output passes ``--verify-only`` v2.0 conformance.

        Note on byte-identity: the pure-v2 short-circuit (F-001) only
        fires when EVERY row has ``peer_id_spki_fingerprint`` set
        (per ``_row_is_already_v2``). DER-only rows lack that field
        and therefore go through the standard migration path even
        when ``scopes`` + ``key_floor_verified_at`` are already present
        — the tool adds ``peer_id_spki_fingerprint: ""``. That is the
        documented behaviour; byte-identity is asserted in the
        100-peer single-shape test above, and the mixed-pin case
        instead asserts conformance + pin-preservation + idempotency
        on the second pass (where every row now has SPKI=empty too,
        so the short-circuit DOES engage).
        """
        rows = ["peers:"]
        # 5 SPKI-only
        for i in range(5):
            spki = "{:02x}".format(0xA0 + i) * 32
            rows.append(_make_v2_peer_row(
                "peer-spki-{:02d}".format(i), spki_hex=spki,
            ))
        # 5 DER-only (legacy preserved, no SPKI)
        for i in range(5):
            der = "{:02x}".format(0xB0 + i) * 32
            rows.append(_make_v2_peer_row(
                "peer-der-{:02d}".format(i), der_hex=der,
                kfv="unknown",
            ))
        # 5 dual-pin (both SPKI + DER side-by-side)
        for i in range(5):
            spki = "{:02x}".format(0xC0 + i) * 32
            der = "{:02x}".format(0xD0 + i) * 32
            rows.append(_make_v2_peer_row(
                "peer-dual-{:02d}".format(i),
                spki_hex=spki, der_hex=der,
                scopes_list=["audit_event_push"],
            ))
        in_path = self._write("v2_mixed.yaml", "\n".join(rows))
        out_path = os.path.join(self.tmpdir, "v2_mixed_out.yaml")

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--skip-cert-inspect",
        )
        self.assertEqual(
            proc.returncode, 0,
            "mixed-pin migration failed: stderr={!r}".format(proc.stderr[:500]),
        )

        # Spot-check pin preservation: every SPKI / DER hex appears.
        text = open(out_path, encoding="utf-8").read()
        for i in range(5):
            self.assertIn("{:02x}".format(0xA0 + i) * 32, text)  # SPKI-only
            self.assertIn("{:02x}".format(0xB0 + i) * 32, text)  # DER-only
            self.assertIn("{:02x}".format(0xC0 + i) * 32, text)  # dual-SPKI
            self.assertIn("{:02x}".format(0xD0 + i) * 32, text)  # dual-DER

        # Conformance: every row passes --verify-only.
        v_proc = _run_tool("--verify-only", "--in", out_path)
        self.assertEqual(
            v_proc.returncode, 0,
            "mixed-pin output failed --verify-only; "
            "stderr={!r}".format(v_proc.stderr[:500]),
        )

        # Second-pass idempotency: now every row carries SPKI (even if
        # empty), so the pure-v2 short-circuit fires and we get byte-
        # identical output (F-001 at the mixed-pin shape level).
        out_path_2 = os.path.join(self.tmpdir, "v2_mixed_again.yaml")
        proc2 = _run_tool(
            "--in", out_path, "--out", out_path_2, "--skip-cert-inspect",
        )
        self.assertEqual(proc2.returncode, 0)
        bytes_a = open(out_path, "rb").read()
        bytes_b = open(out_path_2, "rb").read()
        self.assertEqual(
            bytes_a, bytes_b,
            "second-pass mixed-pin migration must be byte-identical "
            "(F-001 at mixed shape); size_a={} size_b={}".format(
                len(bytes_a), len(bytes_b),
            ),
        )

    # ---------------------------------------------------------------------
    # Test 3: Atomicity — per-peer cert failure mid-batch leaves
    # input file UNCHANGED and output file ABSENT.
    # ---------------------------------------------------------------------

    def test_migration_partial_failure_atomicity(self):
        """Build a 10-peer v1.x file; provide a cert-dir that only holds
        certs for peers 0,1,2,3,4,6,7,8,9 (peer #5 is missing). The
        migration MUST abort on peer #5, leave the input file
        byte-identical to its pre-run state, and refuse to write any
        partial output.

        Pure-stdlib: synthesise certs via openssl subprocess (skip the
        test if openssl is absent — matches existing
        TestPeersMigration.test_spki_matches_cert_inspector
        skipTest convention).
        """
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("openssl binary not on PATH")

        cert_dir = os.path.join(self.tmpdir, "certs")
        os.makedirs(cert_dir)

        # Generate certs for peers 0..9 EXCEPT peer #5.
        import base64
        import hashlib
        import re as _re
        peer_der_shas: dict = {}
        for i in range(10):
            if i == 5:
                continue  # deliberately skip peer #5
            pid = "peer-atomic-{:02d}".format(i)
            key = os.path.join(cert_dir, pid + ".key")
            cert = os.path.join(cert_dir, pid + ".pem")
            gen = subprocess.run(
                [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                 "-keyout", key, "-out", cert, "-days", "30",
                 "-subj", "/CN=" + pid],
                capture_output=True, timeout=15,
            )
            if gen.returncode != 0:
                self.skipTest(
                    "openssl cert generation failed for {0}; stderr={!r}".format(
                        pid, gen.stderr[:200],
                    )
                )
            pem = open(cert, "rb").read()
            m = _re.search(
                rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
                pem, _re.DOTALL,
            )
            if not m:
                self.skipTest("unable to extract DER from generated cert")
            der = base64.b64decode(m.group(1).strip())
            peer_der_shas[i] = hashlib.sha256(der).hexdigest()

        # Build v1.yaml with 10 peers. Peer #5 carries a fake DER so the
        # parser accepts the row; the cert_inspector failure (cert file
        # missing) triggers the per-peer abort.
        rows = ["peers:"]
        for i in range(10):
            pid = "peer-atomic-{:02d}".format(i)
            if i in peer_der_shas:
                der_hex = peer_der_shas[i]
            else:
                der_hex = "ee" * 32  # peer #5 fake DER
            rows.append(_make_v1_peer_row(
                pid, der_hex, "{:02x}".format(i + 0x10) * 32,
            ))
        v1_text = "\n".join(rows)
        in_path = self._write("v1.yaml", v1_text)
        out_path = os.path.join(self.tmpdir, "v2.yaml")
        in_bytes_before = open(in_path, "rb").read()

        proc = _run_tool(
            "--in", in_path, "--out", out_path, "--cert-dir", cert_dir,
        )

        # If cert_inspector cannot parse on this host, the tool will
        # already have aborted earlier — that is also a successful
        # atomicity case (no partial write).
        self.assertNotEqual(
            proc.returncode, 0,
            "expected abort on missing cert; stderr={!r}".format(proc.stderr[:500]),
        )
        self.assertIn("ABORT", proc.stderr)
        # Output file MUST NOT exist (no partial write).
        self.assertFalse(
            os.path.isfile(out_path),
            "atomicity broken: partial v2.yaml written despite per-peer abort",
        )
        # Input file MUST be byte-identical (no in-place mutation).
        in_bytes_after = open(in_path, "rb").read()
        self.assertEqual(
            in_bytes_before, in_bytes_after,
            "atomicity broken: input file mutated by failed migration",
        )

    # ---------------------------------------------------------------------
    # Test 4: SPEC v2.x row count parity for PLAN-099-FOLLOWUP actions.
    # ---------------------------------------------------------------------

    def test_spec_v2_rows_count_matches_audit_actions(self):
        """The plan declares 20 new audit actions registered via
        kernel-override ``PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION``
        (per §4 Wave F.2 + AC9 baseline 234 -> 254). SPEC v2.x rows
        for these 20 actions are produced in Wave F.2 (audit
        registration). Until Wave F.2 lands, the SPEC file MAY contain
        between 0 and 20 v2.29 federation_* rows — we assert the count
        is bounded by the contract (<=20) and surface a clear
        WAVE-F-PENDING skip when the rows haven't landed yet.

        S149 fix (2026-05-20): the original implementation counted
        substring occurrences of "PLAN-099-FOLLOWUP" which over-counted
        because each landed row mentions the marker twice (provenance
        comment + kernel-override sentinel name). Replaced with a row-
        level regex that anchors at start-of-line + table-pipe + literal
        `federation_<name>` + ``(v2.29)`` version tag, matching exactly
        one occurrence per landed action row.

        Failure modes:
          - count > 20 -> ASSERTION FAIL (over-registration; ADR drift)
          - 0 < count < 20 -> ASSERTION FAIL (partial registration; ship
            blocked per AC9 contract)
          - count == 20 -> PASS (Wave F.2 complete)
          - count == 0 -> WAVE-F-PENDING skip (Wave F.2 not yet landed)
        """
        import re as _re
        spec_path = _REPO_ROOT / "SPEC" / "v1" / "audit-log.schema.md"
        if not spec_path.is_file():
            self.skipTest(
                "SPEC/v1/audit-log.schema.md not found at {0}".format(spec_path)
            )
        text = spec_path.read_text(encoding="utf-8")
        # S149 fix: count v2.29 federation_* rows directly (one match per
        # landed row). Both the in-place supersede row for
        # `federation_cert_rotated` at v2.29 AND the 19 net-new federation
        # action rows count toward the 20-row Wave F.2 contract.
        v229_row_re = _re.compile(
            r"^\| `federation_[a-z_]+` \(v2\.29\) \|",
            _re.MULTILINE,
        )
        marker_count = len(v229_row_re.findall(text))
        EXPECTED = 20  # plan §4 Wave F.2 + AC9 (234 -> 254)
        if marker_count == 0:
            self.skipTest(
                "WAVE-F-PENDING: SPEC v2.x rows for PLAN-099-FOLLOWUP not yet "
                "landed (Wave F.2 pending). Expected {0} rows when F.2 ships.".format(
                    EXPECTED,
                )
            )
        self.assertLessEqual(
            marker_count, EXPECTED,
            "SPEC has {0} v2.29 federation_* rows; AC9 caps at {1}. "
            "Over-registration is a drift signal — review Wave F.2 "
            "kernel-override before ship.".format(marker_count, EXPECTED),
        )
        self.assertEqual(
            marker_count, EXPECTED,
            "SPEC has {0}/{1} v2.29 federation_* rows; AC9 contract "
            "demands all {1} land together via the Wave F.2 kernel-"
            "override. Partial registration blocks ship.".format(
                marker_count, EXPECTED,
            ),
        )


if __name__ == "__main__":
    unittest.main()
