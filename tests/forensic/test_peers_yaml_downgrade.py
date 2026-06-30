"""PLAN-099-FOLLOWUP Wave F.1 — peers.yaml downgrade-attack forensics.

Adversarial test surface for the SPKI -> DER downgrade window per
``peers-yaml-schema-migration.md`` §3 + §9. Covers the three F.1
contract cases:

  1. SPKI-pinned peers.yaml read by a v1.x-only loader strips the
     SPKI field -> server enforcement must REFUSE the connection on
     the next handshake (or flag it as legacy-fallback at minimum).
  2. Adversary edits peers.yaml in place to remove
     ``peer_id_spki_fingerprint`` -> the row should be FLAGGED via
     ``federation_peer_invalid_no_fingerprint`` (when DER also absent)
     or ``federation_pin_legacy_used`` (when DER still present), so
     the operator can detect the downgrade.
  3. Owner manually clears SPKI (admin op, not adversarial) -> falls
     back to DER + emits ``federation_pin_legacy_used``. This is the
     LEGITIMATE downgrade path (SPKI was wrong; Owner reverts).

Plus a 4th defense-in-depth case mirroring
``tests/federation/test_spki_dispatcher.py`` in the forensic suite:

  4. peers.yaml has BOTH SPKI + DER; presented cert matches DER but
     not SPKI -> DENY (no downgrade attack window).

Stdlib only. The migration tool is the canonical parse-time validator
so these tests drive it directly via the ``--verify-only`` contract
plus the in-process ``parse_peers_yaml`` / ``verify_v2_conformance``
helpers (which mirror the runtime server's check).

WAVE-F-PENDING markers:
  - Server-side enforcement of "SPKI pinned -> DER not consulted" is
    delivered by Wave C dispatcher (``tests/federation/
    test_spki_dispatcher.py``). The forensic case (4) here is the
    integration mirror; until the dispatcher lands we exercise the
    config-shape invariants only.
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


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOL_PATH = _REPO_ROOT / "tools" / "migrate-peers-yaml.py"


def _load_migrate_module():
    """Load tools/migrate-peers-yaml.py as ``migrate_peers_yaml`` module."""
    spec = importlib.util.spec_from_file_location(
        "migrate_peers_yaml", str(_TOOL_PATH)
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


_migrate = _load_migrate_module()


def _run_tool(*args: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_TOOL_PATH)] + list(args),
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# YAML fixtures
# ---------------------------------------------------------------------------


V2_SPKI_AND_DER_PEER = """\
peers:
  - peer_id: peer-dual-01
    peer_id_spki_fingerprint: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"
    peer_id_cert_fingerprint: "bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222"
    ca_pin_sha256: "ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001"
    scopes: []
    key_floor_verified_at: "2026-05-20T00:00:00Z"
"""

V2_SPKI_ONLY_PEER = """\
peers:
  - peer_id: peer-spki-01
    peer_id_spki_fingerprint: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"
    ca_pin_sha256: "ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01ca01"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001h001"
    scopes: []
    key_floor_verified_at: "2026-05-20T00:00:00Z"
"""


class TestPeersYamlDowngrade(unittest.TestCase):
    """F.1 downgrade forensic tests — config-shape invariants + server-
    enforcement mirror."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="peers-yaml-downgrade-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    # ---------------------------------------------------------------------
    # Test 1: SPKI pin present + v1.x-style strip -> would-be-fallback to
    # DER must be REFUSED when the SPKI pin is set (per §3 dispatcher
    # contract). We exercise the shape-level invariant: a v2.0 row whose
    # SPKI is stripped is no longer a v2.0 row — it is a v1.x row whose
    # `peer_id_cert_fingerprint` is what gets consulted. The server-side
    # dispatcher per Wave C MUST refuse a connection that previously
    # bound to SPKI when the SPKI field is no longer present (downgrade
    # detection).
    # ---------------------------------------------------------------------

    def test_v2_with_spki_pin_refused_as_v1(self):
        """A SPKI-pinned peers.yaml SHOULD parse as v2.0. If we strip
        the SPKI field (simulating a v1.x-only loader), the row drops
        back to DER-fallback territory — which is detectable via the
        ``federation_pin_legacy_used`` audit emit when DER is present,
        and via ``federation_peer_invalid_no_fingerprint`` when neither
        pin is present.

        Forensic contract: stripping SPKI while keeping DER is the
        only way a downgrade attack can be visible to the operator;
        the migration tool's verify-only path here surfaces the shape
        delta deterministically.
        """
        # Baseline: original v2.0 with both pins passes verify.
        original = self._write("v2.yaml", V2_SPKI_AND_DER_PEER)
        proc = _run_tool("--verify-only", "--in", original)
        self.assertEqual(
            proc.returncode, 0,
            "baseline v2.0 (SPKI+DER) must pass verify; stderr={!r}".format(
                proc.stderr,
            ),
        )

        # Adversary strips the SPKI line in place. DER preserved.
        stripped = self._write(
            "v2_stripped.yaml",
            V2_SPKI_AND_DER_PEER.replace(
                '    peer_id_spki_fingerprint: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"\n',
                "",
            ),
        )
        # Verify still succeeds (DER present -> v2.0 invariant met) BUT
        # the SPKI pin is gone. The presence of the legacy DER ALONE on
        # a peer that previously carried SPKI is the downgrade signature
        # the operator must catch via diff/alert in CI or git history.
        proc = _run_tool("--verify-only", "--in", stripped)
        self.assertEqual(proc.returncode, 0)

        # Parse both files and compare: the stripped form lacks SPKI.
        parse = _migrate.parse_peers_yaml
        original_peers = parse(open(original).read())
        stripped_peers = parse(open(stripped).read())
        self.assertEqual(
            original_peers[0].get("peer_id_spki_fingerprint", "")[:8],
            "aaaa1111",
        )
        self.assertNotIn("peer_id_spki_fingerprint", stripped_peers[0])
        # DER preserved in both forms (the downgrade leaves the legacy
        # pin in place, which is precisely the operator detection
        # signature — the row "looks legacy" again).
        self.assertEqual(
            original_peers[0]["peer_id_cert_fingerprint"][:8],
            stripped_peers[0]["peer_id_cert_fingerprint"][:8],
        )

    # ---------------------------------------------------------------------
    # Test 2: SPKI stripped AND no DER -> row REJECTED at parse.
    # ---------------------------------------------------------------------

    def test_stripped_spki_field_rejected(self):
        """When the adversary strips SPKI from a SPKI-only row (no DER
        fallback configured), the resulting peers.yaml MUST fail
        verify-only conformance — neither pin is non-empty, which maps
        to ``federation_peer_invalid_no_fingerprint`` at server parse
        time (per ADR-135-AMEND-1 §5.2)."""
        original = self._write("v2_spki_only.yaml", V2_SPKI_ONLY_PEER)
        proc = _run_tool("--verify-only", "--in", original)
        self.assertEqual(
            proc.returncode, 0,
            "baseline SPKI-only v2.0 must pass verify; stderr={!r}".format(
                proc.stderr,
            ),
        )

        # Adversary strips SPKI; no DER fallback present.
        stripped = self._write(
            "v2_no_pin.yaml",
            V2_SPKI_ONLY_PEER.replace(
                '    peer_id_spki_fingerprint: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"\n',
                "",
            ),
        )
        proc = _run_tool("--verify-only", "--in", stripped)
        self.assertEqual(
            proc.returncode, 7,
            "stripped SPKI w/o DER must trigger EXIT_CONFORMANCE_FAIL=7; "
            "stderr={!r}".format(proc.stderr),
        )
        self.assertIn(
            "missing both peer_id_spki_fingerprint and peer_id_cert_fingerprint",
            proc.stderr,
        )

    # ---------------------------------------------------------------------
    # Test 3: Admin clears SPKI (legitimate downgrade) -> falls back to
    # DER + would emit federation_pin_legacy_used.
    # ---------------------------------------------------------------------

    def test_admin_clears_spki_legacy_fallback_restored(self):
        """LEGITIMATE downgrade path: Owner clears
        ``peer_id_spki_fingerprint`` (e.g. SPKI was set incorrectly and
        the Owner reverts to the DER pin that was working before). The
        row must remain v2.0-conformant AS LONG AS DER is still
        present. The server emits ``federation_pin_legacy_used`` on
        the next handshake (per §3 dispatcher §4 step 3) — this test
        validates the config-shape side: the row still parses and
        still meets the v2.0 invariant.
        """
        v2_with_both = self._write("v2_both.yaml", V2_SPKI_AND_DER_PEER)
        # Owner clears the SPKI by setting it to empty string (the
        # explicit "I am downgrading this peer" gesture).
        downgraded = self._write(
            "v2_downgraded.yaml",
            V2_SPKI_AND_DER_PEER.replace(
                '    peer_id_spki_fingerprint: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"\n',
                '    peer_id_spki_fingerprint: ""\n',
            ),
        )
        # Conformance still passes (DER non-empty -> invariant met).
        proc = _run_tool("--verify-only", "--in", downgraded)
        self.assertEqual(
            proc.returncode, 0,
            "downgraded (SPKI emptied, DER preserved) must pass verify; "
            "stderr={!r}".format(proc.stderr),
        )

        # The DER pin is preserved verbatim and the SPKI is empty.
        parse = _migrate.parse_peers_yaml
        rows = parse(open(downgraded).read())
        self.assertEqual(rows[0].get("peer_id_spki_fingerprint", ""), "")
        self.assertEqual(
            rows[0]["peer_id_cert_fingerprint"][:8], "bbbb2222",
        )

        # Verify_v2_conformance reports OK (DER present, kfv present).
        errs = _migrate.verify_v2_conformance(rows)
        self.assertEqual(
            errs, [],
            "admin-cleared SPKI w/ DER fallback should be v2.0-conformant; "
            "got errors: {!r}".format(errs),
        )

    # ---------------------------------------------------------------------
    # Test 4 (optional, defense-in-depth): SPKI+DER + presented cert
    # matches DER but NOT SPKI -> DENY. Forensic mirror of
    # tests/federation/test_spki_dispatcher.py.
    # ---------------------------------------------------------------------

    def test_downgrade_with_both_pins_present_uses_spki_strict(self):
        """When BOTH SPKI and DER are pinned, the dispatcher MUST
        require SPKI match — DER is not consulted as a fallback (per
        ``peers-yaml-schema-migration.md`` §3 critical-invariant).

        This is the dispatcher-side enforcement (Wave C). The
        forensic copy here asserts the CONFIG SHAPE invariant via the
        migration tool's verify-only path and documents the expected
        server behaviour. The full dispatcher dispatch logic test
        lives at tests/federation/test_spki_dispatcher.py — until
        Wave C dispatcher lands we exercise the shape side only.

        WAVE-F-PENDING: dispatcher integration with this fixture.
        """
        path = self._write("v2_both.yaml", V2_SPKI_AND_DER_PEER)
        proc = _run_tool("--verify-only", "--in", path)
        self.assertEqual(
            proc.returncode, 0,
            "SPKI+DER dual-pin must pass v2.0 verify; stderr={!r}".format(
                proc.stderr,
            ),
        )

        parse = _migrate.parse_peers_yaml
        rows = parse(open(path).read())
        spki = rows[0].get("peer_id_spki_fingerprint", "").strip()
        der = rows[0].get("peer_id_cert_fingerprint", "").strip()
        # Both pins non-empty -> dispatcher MUST consult SPKI only
        # (per §3 step 2 — "SPKI pin set but mismatch -> emit
        # federation_spki_fingerprint_mismatch + DENY (no DER fallback
        # when SPKI declared)").
        self.assertTrue(spki, "SPKI must be non-empty in dual-pin fixture")
        self.assertTrue(der, "DER must be non-empty in dual-pin fixture")
        self.assertNotEqual(
            spki, der,
            "fixture invariant: SPKI and DER differ; downgrade-window "
            "attack requires DISTINCT pins so the dispatcher's "
            "SPKI-strict path is the only legitimate accept path",
        )

        # Dispatcher-side enforcement lives at:
        #   .claude/hooks/_lib/federation/server.py (Wave C)
        #   tests/federation/test_spki_dispatcher.py (Wave C.5)
        # If those modules land before Wave F.1 ships, the forensic
        # mirror MAY import and exercise them directly. For now we
        # leave a WAVE-F-PENDING breadcrumb so the gap is visible.
        dispatcher = (
            _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation" / "server.py"
        )
        dispatcher_test = (
            _REPO_ROOT / "tests" / "federation" / "test_spki_dispatcher.py"
        )
        if not dispatcher.is_file() or not dispatcher_test.is_file():
            self.skipTest(
                "WAVE-F-PENDING: dispatcher (Wave C) not landed; forensic "
                "mirror covers config-shape invariant only. dispatcher={0} "
                "dispatcher_test={1}".format(
                    dispatcher.is_file(), dispatcher_test.is_file(),
                )
            )


if __name__ == "__main__":
    unittest.main()
