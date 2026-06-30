"""test_morning_ledger.py — PLAN-134 W4 proposal-queue bundle format v0.

Covers: Merkle determinism, bundle create/verify round-trip, false-trust
detection (artifact bytes, manifest recommendation, path escape), founder
ledger rendering, nightly producer idempotency, ceremony dry-run +
false-trust abort + baseline arm timing log, ceo-boot renderer fail-open.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / ".claude" / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ml = _load("morning_ledger", "morning_ledger.py")


class _RuntimeDirMixin(TestEnvContext):
    """Isolated CEO_RUNTIME_DIR per test (lesson: mock.patch.dict, never bare assignment)."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory(prefix="w4-ml-test-")
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"CEO_RUNTIME_DIR": self._tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.runtime = Path(self._tmp.name)

    def _make_bundle(self, bundle_id: str = "20990101-demo", verdict: str = "sign",
                     content: bytes = b"hello evidence\n"):
        future = ml.Future(
            name="demo-check", cmd="true", exit_code=0,
            ran_at="2099-01-01T00:00:00Z", duration_ms=5,
            output_sha256=ml._sha256_bytes(content),
        )
        spec = ml.BundleSpec(
            bundle_id=bundle_id, title="Demo bundle", producer="test",
            artifacts=[("out.txt", content)], futures=[future],
            verdict=verdict, why="tudo verde no check mecânico",
        )
        return ml.create_bundle(spec)


class TestMerkle(TestEnvContext):
    def test_deterministic_and_order_sensitive(self):
        a = ml.merkle_root(["aa", "bb", "cc"])
        self.assertEqual(a, ml.merkle_root(["aa", "bb", "cc"]))
        self.assertNotEqual(a, ml.merkle_root(["bb", "aa", "cc"]))

    def test_single_leaf_is_identity(self):
        self.assertEqual(ml.merkle_root(["ab" * 32]), "ab" * 32)

    def test_odd_leaf_promotes(self):
        # 3 leaves: root = H(H(l0+l1) + l2)
        l0, l1, l2 = "00" * 32, "11" * 32, "22" * 32
        inner = ml._sha256_bytes((l0 + l1).encode("ascii"))
        expected = ml._sha256_bytes((inner + l2).encode("ascii"))
        self.assertEqual(ml.merkle_root([l0, l1, l2]), expected)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            ml.merkle_root([])


class TestBundleRoundTrip(_RuntimeDirMixin):
    def test_create_then_deep_verify_ok(self):
        bdir = self._make_bundle()
        manifest = ml.verify_bundle(bdir, deep=True)
        self.assertEqual(manifest["bundle_id"], "20990101-demo")
        self.assertEqual(manifest["recommendation"]["verdict"], "sign")
        self.assertEqual(len(manifest["merkle_root"]), 64)

    def test_duplicate_bundle_id_rejected(self):
        self._make_bundle()
        with self.assertRaises(FileExistsError):
            self._make_bundle()

    def test_invalid_bundle_id_rejected(self):
        with self.assertRaises(ValueError):
            self._make_bundle(bundle_id="../escape")

    def test_artifact_path_escape_rejected(self):
        spec = ml.BundleSpec(
            bundle_id="20990101-esc", title="t", producer="p",
            artifacts=[("../../evil.txt", b"x")],
        )
        with self.assertRaises(ValueError):
            ml.create_bundle(spec)

    def test_invalid_verdict_rejected(self):
        with self.assertRaises(ValueError):
            self._make_bundle(bundle_id="20990101-v", verdict="maybe")


class TestFalseTrust(_RuntimeDirMixin):
    def test_artifact_byte_mutation_caught_deep(self):
        bdir = self._make_bundle()
        art = bdir / "artifacts" / "out.txt"
        art.write_bytes(art.read_bytes() + b"X")
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=True)
        # fast mode (manifest-only) deliberately does NOT catch byte drift
        ml.verify_bundle(bdir, deep=False)

    def test_recommendation_edit_caught_even_fast(self):
        bdir = self._make_bundle()
        mpath = bdir / "manifest.json"
        data = json.loads(mpath.read_text())
        data["recommendation"]["verdict"] = "dont-sign"
        mpath.write_text(json.dumps(data, indent=2, sort_keys=True))
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=False)

    def test_manifest_artifact_path_escape_caught(self):
        bdir = self._make_bundle()
        mpath = bdir / "manifest.json"
        data = json.loads(mpath.read_text())
        data["artifacts"][0]["path"] = "../../../etc/passwd"
        mpath.write_text(json.dumps(data, indent=2, sort_keys=True))
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=True)

    def test_missing_artifact_caught(self):
        bdir = self._make_bundle()
        (bdir / "artifacts" / "out.txt").unlink()
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=True)

    def test_title_edit_caught_even_fast(self):
        # Codex R1 P1: metadata is Merkle-bound — a retitle trips the root.
        bdir = self._make_bundle()
        mpath = bdir / "manifest.json"
        data = json.loads(mpath.read_text())
        data["title"] = "Título adulterado"
        mpath.write_text(json.dumps(data, indent=2, sort_keys=True))
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=False)

    def test_artifact_repath_caught_even_fast(self):
        # Codex R1 P1: artifact PATH is in the leaf, not just the content hash.
        bdir = self._make_bundle()
        mpath = bdir / "manifest.json"
        data = json.loads(mpath.read_text())
        data["artifacts"][0]["path"] = "artifacts/renamed.txt"
        mpath.write_text(json.dumps(data, indent=2, sort_keys=True))
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=False)

    def test_symlink_artifact_caught_deep(self):
        # Codex R1 P1: symlinked artifact must be rejected even when the
        # link target's bytes hash correctly.
        bdir = self._make_bundle()
        art = bdir / "artifacts" / "out.txt"
        content = art.read_bytes()
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_bytes(content)
        art.unlink()
        art.symlink_to(outside)
        with self.assertRaises(ml.FalseTrustError):
            ml.verify_bundle(bdir, deep=True)


class TestRender(_RuntimeDirMixin):
    def test_empty_queue_message(self):
        self.assertIn("Fila vazia", ml.render_ledger())

    def test_founder_language_row(self):
        self._make_bundle()
        out = ml.render_ledger()
        self.assertIn("ASSINAR", out)
        self.assertIn("1/1 ok", out)
        self.assertIn("Demo bundle", out)

    def test_corrupt_bundle_renders_dont_sign_not_crash(self):
        bdir = self._make_bundle()
        (bdir / "manifest.json").write_text("{not json")
        out = ml.render_ledger()
        self.assertIn("NAO ASSINAR", out)

    def test_truncation_cap(self):
        for i in range(12):
            self._make_bundle(bundle_id=f"20990101-b{i:02d}")
        out = ml.render_ledger(max_bundles=10)
        self.assertIn("+2 proposta(s)", out)

    def test_sanitize_strips_controls_and_bounds(self):
        s = ml.sanitize_text("a\x1b[31m\nb" + "c" * 500)
        self.assertNotIn("\x1b", s)
        self.assertNotIn("\n", s)
        self.assertLessEqual(len(s), 200)


class TestNightlyProducer(_RuntimeDirMixin):
    def setUp(self):
        super().setUp()
        self.np = _load("nightly_proposals", "nightly-proposals.py")
        # Replace real (slow) producers with one fast fake.
        patcher = mock.patch.object(
            self.np, "PRODUCERS",
            [("fake", "Fake check", lambda cwd: (0, b"ok\n", 1), "fake.txt", "passou", "falhou")],
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_produces_then_skips_on_rerun(self):
        first = self.np.build_night(date="20990102")
        self.assertEqual(len(first), 1)
        self.assertIn("queued", first[0])
        again = self.np.build_night(date="20990102")
        self.assertIn("SKIP", again[0])

    def test_staleness_degraded_advisory_yields_honest_why(self):
        # PREREG-W4 Amendment #1: exit 0 + findings>0 must NOT say "limpa".
        payload = json.dumps({"status": "degraded", "findings_count": 1}).encode()
        verdict, why = self.np._staleness_why(0, payload)
        self.assertEqual(verdict, "sign")
        self.assertIn("1 achado", why)
        self.assertNotIn("limpa", why)

    def test_staleness_clean_says_clean(self):
        payload = json.dumps({"status": "ok", "findings_count": 0}).encode()
        verdict, why = self.np._staleness_why(0, payload)
        self.assertEqual(verdict, "sign")
        self.assertIn("limpa", why)

    def test_staleness_unreadable_artifact_dont_sign(self):
        verdict, why = self.np._staleness_why(0, b"{not json")
        self.assertEqual(verdict, "dont-sign")

    def test_failing_check_yields_dont_sign(self):
        with mock.patch.object(
            self.np, "PRODUCERS",
            [("bad", "Bad check", lambda cwd: (3, b"boom\n", 1), "bad.txt", "passou", "falhou")],
        ):
            self.np.build_night(date="20990103")
        manifest = ml.load_manifest(ml.queue_dir() / "20990103-bad")
        self.assertEqual(manifest["recommendation"]["verdict"], "dont-sign")
        self.assertEqual(manifest["futures"][0]["exit_code"], 3)


class TestCeremony(_RuntimeDirMixin):
    def setUp(self):
        super().setUp()
        self.mc = _load("morning_ceremony", "morning-ceremony.py")

    def test_dry_run_yes_writes_ratification_keeps_queue(self):
        self._make_bundle()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.mc.run_ceremony(dry_run=True, auto_yes=True)
        self.assertEqual(rc, 0)
        recs = list(ml.ratifications_dir().glob("ratification-*.json"))
        self.assertEqual(len(recs), 1)
        record = json.loads(recs[0].read_text())
        self.assertTrue(record["dry_run"])
        self.assertEqual(len(record["combined_root"]), 64)
        # dry-run leaves the queue intact
        self.assertEqual(len(ml.pending_bundles()), 1)
        # timing row appended
        log = (ml.runtime_dir() / "dryrun-log.jsonl").read_text().strip().splitlines()
        self.assertEqual(json.loads(log[-1])["arm"], "ceremony")

    def test_false_trust_aborts_exit_2_and_logs(self):
        bdir = self._make_bundle()
        art = bdir / "artifacts" / "out.txt"
        art.write_bytes(art.read_bytes() + b"X")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.mc.run_ceremony(dry_run=True, auto_yes=True)
        self.assertEqual(rc, 2)
        self.assertIn("FALSE-TRUST", buf.getvalue())
        log = (ml.runtime_dir() / "dryrun-log.jsonl").read_text()
        self.assertIn("false_trust", log)
        # nothing ratified
        self.assertEqual(list(ml.ratifications_dir().glob("*.json")) if ml.ratifications_dir().is_dir() else [], [])

    def test_baseline_arm_logs_timing(self):
        self._make_bundle()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.mc.run_baseline(auto_yes=True)
        self.assertEqual(rc, 0)
        row = json.loads((ml.runtime_dir() / "dryrun-log.jsonl").read_text().strip().splitlines()[-1])
        self.assertEqual(row["arm"], "baseline")
        self.assertTrue(row["automated"])

    def test_empty_queue_noop(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(self.mc.run_ceremony(dry_run=True, auto_yes=True), 0)
        self.assertIn("Fila vazia", buf.getvalue())

    def test_mutation_during_prompt_caught_by_reverify(self):
        # Codex R1 P0 #2: bytes changing while the Owner sits at the prompt
        # must abort BEFORE anything is signed.
        bdir = self._make_bundle()
        art = bdir / "artifacts" / "out.txt"

        def _mutate_then_approve(auto_yes):
            art.write_bytes(art.read_bytes() + b"X")
            return True

        buf = io.StringIO()
        with mock.patch.object(self.mc, "_prompt_decision", _mutate_then_approve):
            with redirect_stdout(buf):
                rc = self.mc.run_ceremony(dry_run=True, auto_yes=False)
        self.assertEqual(rc, 2)
        self.assertIn("FALSE-TRUST", buf.getvalue())
        self.assertFalse(list(ml.ratifications_dir().glob("*.json")) if ml.ratifications_dir().is_dir() else [])

    def test_real_sign_path_verifies_bytes_and_signature_then_archives(self):
        # Codex R1 P0 #1: the signed record must be byte-identical to what
        # the ceremony wrote, and the signature must verify, before archive.
        self._make_bundle()
        calls = []

        def _fake_gpg(cmd, **kw):
            calls.append(cmd[:2])
            if "--detach-sign" in cmd:
                Path(cmd[-1] + ".asc").write_text("fake-sig")
            return mock.Mock(returncode=0)

        buf = io.StringIO()
        with mock.patch.object(self.mc.subprocess, "run", _fake_gpg):
            with redirect_stdout(buf):
                rc = self.mc.run_ceremony(dry_run=False, auto_yes=True)
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 2)  # sign + verify
        # archived out of the queue
        self.assertEqual(ml.pending_bundles(), [])
        self.assertTrue(any(ml.ratified_dir().rglob("manifest.json")))

    def test_failed_signature_verification_aborts_without_archive(self):
        self._make_bundle()

        def _fake_gpg(cmd, **kw):
            if "--detach-sign" in cmd:
                Path(cmd[-1] + ".asc").write_text("fake-sig")
                return mock.Mock(returncode=0)
            return mock.Mock(returncode=2)  # --verify fails

        buf = io.StringIO()
        with mock.patch.object(self.mc.subprocess, "run", _fake_gpg):
            with redirect_stdout(buf):
                rc = self.mc.run_ceremony(dry_run=False, auto_yes=True)
        self.assertEqual(rc, 2)
        self.assertIn("FALSE-TRUST", buf.getvalue())
        self.assertEqual(len(ml.pending_bundles()), 1)  # nothing archived


class TestLockAndCrashSafety(_RuntimeDirMixin):
    def test_pending_ignores_tmp_dirs(self):
        self._make_bundle()
        tmp = ml.queue_dir() / ".tmp-crash-residue"
        (tmp / "artifacts").mkdir(parents=True)
        self.assertEqual(len(ml.pending_bundles()), 1)

    def test_producer_nonblocking_lock_raises_when_held(self):
        np = _load("nightly_proposals_lock", "nightly-proposals.py")
        with ml.runtime_lock():
            with self.assertRaises(RuntimeError):
                np.build_night(date="20990104")


class TestCeoBootRenderer(_RuntimeDirMixin):
    def setUp(self):
        super().setUp()
        # ceo-boot resolves morning_ledger from sys.modules first — keep ours.
        self.boot = _load("ceo_boot_w4", "ceo-boot.py")

    def test_empty_queue_renders_nothing(self):
        self.assertEqual(self.boot._render_morning_ledger_safe(), "")

    def test_pending_bundle_renders_section(self):
        self._make_bundle()
        out = self.boot._render_morning_ledger_safe()
        self.assertIn("Morning Ledger", out)
        self.assertIn("ASSINAR", out)

    def test_kill_switch_env(self):
        self._make_bundle()
        with mock.patch.dict(os.environ, {"CEO_BOOT_LEDGER": "0"}):
            self.assertEqual(self.boot._render_morning_ledger_safe(), "")

    def test_fail_open_on_renderer_crash(self):
        self._make_bundle()
        with mock.patch.object(sys.modules["morning_ledger"], "render_ledger",
                               side_effect=RuntimeError("boom")):
            self.assertEqual(self.boot._render_morning_ledger_safe(), "")


if __name__ == "__main__":
    unittest.main()
