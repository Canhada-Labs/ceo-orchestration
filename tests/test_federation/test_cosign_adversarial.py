"""PLAN-112-FOLLOWUP-federation-wire (PHASE2) — REMAINING #3 + #4.

#3 (AC15): the ``.inflight`` 5-minute reaper reverts orphaned co-sign
    markers (residual hard-crash-between-renames window) so a destructive
    co-sign is never left stuck.
#4 (AC5): adversarial Gate #10a — forged signature, TTL-expired, missing
    signed_at, and replayed/consumed sentinel are all rejected, and the
    .inflight pair is reverted on every verify-failure path.

Stdlib-only; deterministic (no time.sleep; mtime is set explicitly).
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

try:
    from _lib.federation import server as _SRV  # type: ignore
except Exception:  # pragma: no cover
    _SRV = None  # type: ignore


# ---------------------------------------------------------------------------
# Reaper tests (REMAINING #3 / AC15) — module-level function, no handler.
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestInflightReaper(unittest.TestCase):
    def _mk_sentinels_dir(self):
        d = tempfile.mkdtemp(prefix="fed-reap-")
        self.addCleanup(lambda: _rmtree(d))
        return Path(d)

    def _mk_inflight(self, base: Path, sigref: str, name: str, age_s: float):
        sub = base / sigref
        sub.mkdir(parents=True, exist_ok=True)
        f = sub / name
        f.write_text("x", encoding="utf-8")
        old = time.time() - age_s
        os.utime(f, (old, old))
        return f

    def _orphaned(self, sub):
        return list(sub.glob("*.orphaned-*"))

    def test_quarantines_orphan_older_than_5min(self):
        base = self._mk_sentinels_dir()
        f = self._mk_inflight(base, "abc", "approval.md.inflight", age_s=600)
        n = _SRV._reap_orphaned_inflight(base)
        self.assertEqual(n, 1)
        self.assertFalse(f.exists())
        # Quarantined to a TERMINAL marker — NOT resurrected to approval.md
        # (Codex AC18 P1: no destructive co-sign resurrection).
        self.assertFalse((base / "abc" / "approval.md").exists())
        self.assertTrue(self._orphaned(base / "abc"))

    def test_quarantines_asc_orphan(self):
        base = self._mk_sentinels_dir()
        self._mk_inflight(base, "abc", "approval.md.asc.inflight", age_s=600)
        _SRV._reap_orphaned_inflight(base)
        self.assertFalse((base / "abc" / "approval.md.asc").exists())
        self.assertTrue(self._orphaned(base / "abc"))

    def test_leaves_fresh_inflight_untouched(self):
        base = self._mk_sentinels_dir()
        f = self._mk_inflight(base, "abc", "approval.md.inflight", age_s=10)
        n = _SRV._reap_orphaned_inflight(base)
        self.assertEqual(n, 0)
        self.assertTrue(f.exists())  # still in-flight, not quarantined

    def test_quarantines_even_when_original_exists(self):
        # A fresh approval.md must NOT block quarantine of a stale orphan,
        # and must itself be preserved (never clobbered).
        base = self._mk_sentinels_dir()
        sub = base / "abc"
        sub.mkdir(parents=True)
        (sub / "approval.md").write_text("orig", encoding="utf-8")
        f = self._mk_inflight(base, "abc", "approval.md.inflight", age_s=600)
        n = _SRV._reap_orphaned_inflight(base)
        self.assertEqual(n, 1)
        self.assertFalse(f.exists())
        self.assertTrue((sub / "approval.md").exists())  # preserved
        self.assertTrue(self._orphaned(sub))

    def test_none_dir_is_noop(self):
        self.assertEqual(_SRV._reap_orphaned_inflight(None), 0)

    def test_missing_dir_is_noop(self):
        self.assertEqual(
            _SRV._reap_orphaned_inflight(Path("/nonexistent/reap/xyz")), 0
        )

    def test_custom_max_age(self):
        base = self._mk_sentinels_dir()
        self._mk_inflight(base, "abc", "approval.md.inflight", age_s=120)
        # 60s threshold → the 120s-old marker IS quarantined.
        n = _SRV._reap_orphaned_inflight(base, max_age_seconds=60.0)
        self.assertEqual(n, 1)


# ---------------------------------------------------------------------------
# Adversarial Gate #10a cosign tests (REMAINING #4 / AC5).
# ---------------------------------------------------------------------------


class _HeaderMap(dict):
    def get(self, k, default=None):
        for kk, vv in self.items():
            if kk.lower() == str(k).lower():
                return vv
        return default


class _FakeServer:
    def __init__(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            setattr(self, k, v)


def _rmtree(path: str) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestCosignAdversarial(unittest.TestCase):
    def setUp(self):
        self._saved_verify = _SRV.verify_enable_sentinel_pair
        self.addCleanup(self._restore)
        self._tmp = tempfile.mkdtemp(prefix="fed-cosign-")
        self.addCleanup(lambda: _rmtree(self._tmp))
        self._sent_dir = Path(self._tmp) / "sentinels"

    def _restore(self):
        _SRV.verify_enable_sentinel_pair = self._saved_verify

    def _mk_sentinel(self, sigref: str, signed_at_iso: Optional[str]):
        sub = self._sent_dir / sigref
        sub.mkdir(parents=True, exist_ok=True)
        body = "approval\n"
        if signed_at_iso is not None:
            body += 'signed_at: "{0}"\n'.format(signed_at_iso)
        (sub / "approval.md").write_text(body, encoding="utf-8")
        (sub / "approval.md.asc").write_text("-sig-", encoding="utf-8")
        return sub

    def _handler(self, sigref_header: Optional[str]):
        h = _SRV._FederationHandler.__new__(_SRV._FederationHandler)
        headers = {}
        if sigref_header is not None:
            headers["X-CEO-Owner-Sigref"] = sigref_header
        h.headers = _HeaderMap(headers)
        h.server = _FakeServer(
            federation_sentinels_dir=self._sent_dir,
            owner_fpr="OWNERFPR",
            signer_registry_path=None,
            federation_config=None,
        )
        return h

    def test_missing_sigref_header_rejected(self):
        h = self._handler(sigref_header=None)
        ok, reason, paths = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertEqual(paths, None)
        self.assertIn("missing_header", reason)

    def test_sigref_charset_rejected(self):
        h = self._handler(sigref_header="../../etc/passwd")
        ok, reason, _ = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertIn("sigref_charset", reason)

    def test_sentinel_not_found_rejected(self):
        self._sent_dir.mkdir(parents=True, exist_ok=True)
        h = self._handler(sigref_header="nope")
        ok, reason, _ = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertIn("sentinel_not_found", reason)

    def test_forged_signature_rejected_and_reverted(self):
        sub = self._mk_sentinel("good", _iso_now())
        _SRV.verify_enable_sentinel_pair = lambda *a, **k: (False, "bad_sig")
        h = self._handler(sigref_header="good")
        ok, reason, _ = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertIn("verify_failed", reason)
        # .inflight reverted to original (P2 #4) — re-drivable.
        self.assertTrue((sub / "approval.md").exists())
        self.assertTrue((sub / "approval.md.asc").exists())
        self.assertFalse((sub / "approval.md.inflight").exists())

    def test_ttl_expired_rejected_and_reverted(self):
        old = _iso_offset(-25 * 3600)  # 25h ago > 24h TTL
        sub = self._mk_sentinel("aged", old)
        _SRV.verify_enable_sentinel_pair = lambda *a, **k: (True, "ok")
        h = self._handler(sigref_header="aged")
        ok, reason, _ = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertIn("ttl_expired", reason)
        self.assertTrue((sub / "approval.md").exists())

    def test_missing_signed_at_rejected_and_reverted(self):
        sub = self._mk_sentinel("nosigat", signed_at_iso=None)
        _SRV.verify_enable_sentinel_pair = lambda *a, **k: (True, "ok")
        h = self._handler(sigref_header="nosigat")
        ok, reason, _ = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_signed_at")
        self.assertTrue((sub / "approval.md").exists())

    def test_valid_then_replay_after_consume_rejected(self):
        sub = self._mk_sentinel("fresh", _iso_now())
        _SRV.verify_enable_sentinel_pair = lambda *a, **k: (True, "ok")
        h = self._handler(sigref_header="fresh")
        ok, reason, paths = h._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertTrue(ok, reason)
        # Consume it (Gate #10b).
        h._consume_owner_cosign_sentinel(paths)
        self.assertFalse((sub / "approval.md").exists())
        self.assertFalse((sub / "approval.md.inflight").exists())
        # Replay: same sigref now resolves to nothing → rejected.
        h2 = self._handler(sigref_header="fresh")
        ok2, reason2, _ = h2._verify_owner_cosign_claim(
            "POST", "/federation/peer-revoke"
        )
        self.assertFalse(ok2)
        self.assertIn("sentinel_not_found", reason2)


def _iso_now() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_offset(seconds: float) -> str:
    import datetime as dt
    t = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    unittest.main()
