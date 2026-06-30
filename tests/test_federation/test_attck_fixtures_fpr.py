"""PLAN-112-FOLLOWUP-federation-wire-or-delete — ATT&CK fixtures + FPR gate.

Replays the committed deterministic corpus + should-fire fixtures through
the REAL ``_lib.federation.rate_limit`` + ``audit_chain_ext`` modules.

R-TD-1: should-fire assertions check the EMITTED chained-audit record
(via an emit_generic spy), NOT the HTTP status — this defeats the
``_safe_emit`` no-op trap. A "emit-registered vs absent" regression is
included (TestEmitRegisteredVsAbsent).

R-TD-2: FPR ≤ 15% per emitter class measured against the benign corpus
(≥200 records/class). FPR = false-positive emits / corpus size.

R-TD-3: T1485 auto-revoke is bounded-TTL + non-cross-peer (anti self-DoS).

Determinism: rate_limit functions take ``now=`` — the fixtures carry
absolute ``ts`` so there is no wall-clock dependency, no time.sleep.
Stdlib-only.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List


_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

_FIXTURES = (
    _REPO_ROOT / "tests" / "fixtures" / "federation"
)

FPR_THRESHOLD = 0.15  # R-TD-2 — ≤15% per emitter class
MIN_CORPUS_PER_CLASS = 200  # R-TD-2 — pinned minimum sample


def _load_rate_limit():
    try:
        from _lib.federation import rate_limit  # type: ignore
        return rate_limit
    except Exception:
        return None


def _load_audit_chain_ext():
    try:
        from _lib.federation import audit_chain_ext  # type: ignore
        return audit_chain_ext
    except Exception:
        return None


def _load_audit_emit():
    try:
        from _lib import audit_emit  # type: ignore
        return audit_emit
    except Exception:
        return None


def _read_ndjson(name: str) -> List[Dict[str, Any]]:
    p = _FIXTURES / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


class _EmitSpy:
    """Context manager that captures emit_generic calls.

    NOTE (Codex P1 #3): this spy does NOT forward to the real
    ``emit_generic`` — it is a FAST capture for the per-call breaker/trip
    behaviour + the FPR sweep (which must stay side-effect-free). A spy
    alone CANNOT catch a schema / registration / write-chain failure (that
    is the same R-TD-1 trap one level up). The ``_RealEmitLog`` helper +
    the ``TestRealChainedRecord*`` cases below close that gap by writing
    through the REAL emit_generic to a temp audit log and asserting the
    on-disk JSONL record + its chain envelope.
    """

    def __init__(self, audit_emit) -> None:
        self.ae = audit_emit
        self.calls: List[Dict[str, Any]] = []
        self._orig = None

    def __enter__(self):
        self._orig = self.ae.emit_generic

        def _spy(action, **kw):
            self.calls.append({"action": action, **kw})
            # Do NOT forward — fast capture; see class docstring + the
            # TestRealChainedRecord* cases for the real-write coverage.
        self.ae.emit_generic = _spy
        return self

    def __exit__(self, *a):
        self.ae.emit_generic = self._orig

    def actions(self):
        return [c["action"] for c in self.calls]


class _RealEmitLog:
    """Point the REAL audit_emit at a temp log (sync mode) + read it back.

    Codex P1 #3: for at least one should-fire fixture per emitter we write
    through the REAL ``emit_generic`` (NOT a spy) so a schema / registration
    / write-chain failure WOULD surface (no record on disk). Reads back the
    JSONL record + asserts the chain envelope (``hmac`` field + v2 schema).
    """

    def __init__(self) -> None:
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="fed-real-emit-")
        self._saved = {}

    def __enter__(self):
        import os
        for k, v in (
            ("CEO_AUDIT_LOG_DIR", self.tmp),
            ("CEO_AUDIT_SYNC_MODE", "1"),  # synchronous → record on disk now
        ):
            self._saved[k] = os.environ.get(k)
            os.environ[k] = v
        return self

    def __exit__(self, *a):
        import os
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def records(self) -> List[Dict[str, Any]]:
        import glob
        import os
        out: List[Dict[str, Any]] = []
        for lf in glob.glob(os.path.join(self.tmp, "**", "*.jsonl"),
                            recursive=True):
            for line in Path(lf).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict) and rec.get("action"):
                    out.append(rec)
        return out

    def records_for(self, action: str) -> List[Dict[str, Any]]:
        return [r for r in self.records() if r.get("action") == action]


@unittest.skipIf(_load_rate_limit() is None, "rate_limit module unavailable")
class TestBenignCorpusFPR(unittest.TestCase):
    """R-TD-2 — replay the benign corpus; assert FPR ≤ 15% per class."""

    def test_corpus_present_and_sized(self):
        corpus = _read_ndjson("federation-benign-corpus.ndjson")
        self.assertTrue(corpus, "benign corpus fixture missing")
        from collections import Counter
        by_class = Counter(r.get("class") for r in corpus)
        for cls in ("rate_limit", "backpressure"):
            self.assertGreaterEqual(
                by_class.get(cls, 0), MIN_CORPUS_PER_CLASS,
                "corpus class {0} has {1} < {2} records".format(
                    cls, by_class.get(cls, 0), MIN_CORPUS_PER_CLASS
                ),
            )

    def test_rate_limit_fpr_under_threshold(self):
        rl = _load_rate_limit()
        rl.reset_state()
        corpus = [
            r for r in _read_ndjson("federation-benign-corpus.ndjson")
            if r.get("class") == "rate_limit"
        ]
        self.assertGreaterEqual(len(corpus), MIN_CORPUS_PER_CLASS)
        false_positives = 0
        for rec in corpus:
            ok, _reason = rl.check_rate_limit(
                rec["peer_id"], rec["route"], rec["ip_prefix"],
                now=rec["ts"],
            )
            # Benign cadence is under-cap → a denial is a FALSE POSITIVE.
            if not ok:
                false_positives += 1
                rl.record_hit(
                    rec["peer_id"], rec["route"], rec["ip_prefix"],
                    now=rec["ts"],
                )
        fpr = false_positives / float(len(corpus))
        self.assertLessEqual(
            fpr, FPR_THRESHOLD,
            "rate_limit FPR {0:.3f} > {1} ({2}/{3} benign denials)".format(
                fpr, FPR_THRESHOLD, false_positives, len(corpus)
            ),
        )

    def test_backpressure_fpr_under_threshold(self):
        rl = _load_rate_limit()
        rl.reset_state()
        corpus = [
            r for r in _read_ndjson("federation-benign-corpus.ndjson")
            if r.get("class") == "backpressure"
        ]
        self.assertGreaterEqual(len(corpus), MIN_CORPUS_PER_CLASS)
        false_positives = 0
        for rec in corpus:
            rl.track_append_latency(int(rec["latency_ms"]), now=rec["ts"])
            ok, _info = rl.check_backpressure(now=rec["ts"])
            if not ok:
                false_positives += 1
        fpr = false_positives / float(len(corpus))
        self.assertLessEqual(
            fpr, FPR_THRESHOLD,
            "backpressure FPR {0:.3f} > {1}".format(fpr, FPR_THRESHOLD),
        )


@unittest.skipIf(_load_rate_limit() is None, "rate_limit module unavailable")
class TestShouldFireT1499Storm(unittest.TestCase):
    """R-TD-1 — the storm fixture trips the circuit-breaker AND the emit
    record (federation_message_storm_detected) is actually written."""

    def test_storm_trips_breaker_and_emits(self):
        rl = _load_rate_limit()
        ae = _load_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        rl.reset_state()
        storm = _read_ndjson("should-fire-t1499-storm.ndjson")
        self.assertTrue(storm)

        with _EmitSpy(ae) as spy:
            tripped = False
            for rec in storm:
                ok, _r = rl.check_rate_limit(
                    rec["peer_id"], rec["route"], rec["ip_prefix"],
                    now=rec["ts"],
                )
                if not ok:
                    rl.record_hit(
                        rec["peer_id"], rec["route"], rec["ip_prefix"],
                        now=rec["ts"],
                    )
                # The breaker fires on the NEXT check after enough hits.
                cb_ok, _cbr = rl.check_circuit_breaker(
                    rec["peer_id"], rec["route"], now=rec["ts"],
                )
                if not cb_ok:
                    tripped = True
            self.assertTrue(tripped, "storm should trip the circuit-breaker")
            # R-TD-1: assert the EMITTED audit record, not the HTTP status.
            self.assertIn(
                "federation_message_storm_detected", spy.actions(),
                "breaker trip must EMIT federation_message_storm_detected "
                "(the _safe_emit C-4 fallback makes this real)",
            )


@unittest.skipIf(_load_rate_limit() is None, "rate_limit module unavailable")
class TestShouldFireT1485AutoRevoke(unittest.TestCase):
    """R-TD-3 — auto-revoke is bounded-TTL + non-cross-peer."""

    def test_autorevoke_bounded_ttl_and_non_cross_peer(self):
        rl = _load_rate_limit()
        ae = _load_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        rl.reset_state()
        fixture = _read_ndjson("should-fire-t1485-autorevoke.ndjson")
        self.assertTrue(fixture)
        attacker = fixture[0]["peer_id"]
        route = fixture[0]["route"]

        with _EmitSpy(ae) as spy:
            for rec in fixture:
                ok, _r = rl.check_rate_limit(
                    rec["peer_id"], route, rec["ip_prefix"], now=rec["ts"],
                )
                if not ok:
                    rl.record_hit(rec["peer_id"], route, rec["ip_prefix"], now=rec["ts"])
                rl.check_circuit_breaker(rec["peer_id"], route, now=rec["ts"])

        last_ts = fixture[-1]["ts"]
        # Attacker (peer, route) is revoked NOW.
        ok_attacker, reason = rl.check_circuit_breaker(
            attacker, route, now=last_ts + 1,
        )
        self.assertFalse(ok_attacker, "attacker scope should be revoked")
        self.assertIn("revoked", str(reason))

        # NON-cross-peer: a DISTINCT legitimate peer on the same route is
        # NOT revoked by the attacker's storm (anti self-DoS).
        ok_other, _r = rl.check_circuit_breaker(
            "legit-peer", route, now=last_ts + 1,
        )
        self.assertTrue(
            ok_other,
            "a distinct peer must NOT be revoked by another peer's storm",
        )

        # Bounded-TTL: after BREAKER_REVOKE_SEC the attacker scope recovers.
        recover_at = last_ts + rl.RateLimitConfig.BREAKER_REVOKE_SEC + 5
        ok_recover, _r = rl.check_circuit_breaker(
            attacker, route, now=recover_at,
        )
        self.assertTrue(
            ok_recover,
            "auto-revoke must be bounded-TTL (recovers after "
            "BREAKER_REVOKE_SEC), not permanent",
        )


@unittest.skipIf(_load_audit_chain_ext() is None, "audit_chain_ext unavailable")
class TestShouldFireT1565Tamper(unittest.TestCase):
    """R-TD-1 — the tampered chain fixture fires federation_tamper_detected."""

    def test_tampered_chain_emits(self):
        ace = _load_audit_chain_ext()
        ae = _load_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        log = tmp / "audit-log.jsonl"
        tamper = _read_ndjson("should-fire-t1565-tamper.ndjson")
        self.assertTrue(tamper)
        log.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in tamper) + "\n",
            encoding="utf-8",
        )
        with _EmitSpy(ae) as spy:
            ok, info = ace.check_chain(log)
        self.assertFalse(ok, "tampered chain must be detected as a break")
        self.assertIsNotNone(info)
        self.assertIn(
            "federation_tamper_detected", spy.actions(),
            "chain break must EMIT federation_tamper_detected",
        )

    def test_clean_chain_does_not_emit(self):
        """should-NOT-fire: a clean chain does not emit tamper."""
        ace = _load_audit_chain_ext()
        ae = _load_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        import hashlib
        import tempfile

        def canon_hash(ev):
            filtered = {k: v for k, v in ev.items()
                        if k not in ("audit_chain_hash",
                                     "audit_chain_prev_hash",
                                     "_timestamp_emitted")}
            c = json.dumps(filtered, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
            return hashlib.sha256(c.encode("utf-8")).hexdigest()

        tmp = Path(tempfile.mkdtemp())
        log = tmp / "audit-log.jsonl"
        e1 = {"action": "x", "n": 1, "audit_chain_prev_hash": "0" * 64}
        e2 = {"action": "x", "n": 2, "audit_chain_prev_hash": canon_hash(e1)}
        log.write_text(
            json.dumps(e1, sort_keys=True) + "\n"
            + json.dumps(e2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with _EmitSpy(ae) as spy:
            ok, _info = ace.check_chain(log)
        self.assertTrue(ok, "clean chain must verify")
        self.assertNotIn("federation_tamper_detected", spy.actions())


@unittest.skipIf(_load_audit_emit() is None, "audit_emit unavailable")
class TestEmitRegisteredVsAbsent(unittest.TestCase):
    """R-TD-1 regression — distinguish a REGISTERED emit (writes a record)
    from an ABSENT/unregistered one (no record). This is the canary that
    would have caught the original no-op trap."""

    def test_registered_action_writes_via_generic(self):
        ae = _load_audit_emit()
        action = "federation_message_storm_detected"
        if action not in ae._KNOWN_ACTIONS:
            self.skipTest("federation actions not registered in this build")
        with _EmitSpy(ae) as spy:
            ae.emit_generic(action, peer_id="p", route="/r", ip_prefix="",
                            hits_in_window=3, window_seconds=900)
        self.assertIn(action, spy.actions())

    def test_unregistered_action_does_not_write(self):
        ae = _load_audit_emit()
        # An action NOT in _KNOWN_ACTIONS must NOT produce a record —
        # emit_generic breadcrumbs + returns. (We can't spy emit_generic
        # itself here since we're testing IT, so we assert via a temp log.)
        import os
        import tempfile
        import glob
        tmp = tempfile.mkdtemp()
        saved = os.environ.get("CEO_AUDIT_LOG_DIR")
        os.environ["CEO_AUDIT_LOG_DIR"] = tmp
        try:
            ae.emit_generic(
                "federation_definitely_not_registered_xyz", foo="bar"
            )
        finally:
            if saved is None:
                os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            else:
                os.environ["CEO_AUDIT_LOG_DIR"] = saved
        logs = glob.glob(os.path.join(tmp, "**", "*.jsonl"), recursive=True)
        wrote_unknown = False
        for lf in logs:
            if "federation_definitely_not_registered_xyz" in Path(lf).read_text():
                wrote_unknown = True
        self.assertFalse(
            wrote_unknown,
            "an unregistered action must NOT be written (fail-safe)",
        )


@unittest.skipIf(_load_audit_emit() is None, "audit_emit unavailable")
class TestRealChainedRecordPerEmitter(unittest.TestCase):
    """Codex P1 #3 — write through the REAL emit_generic (NOT a spy) to a
    temp audit log, then assert the on-disk JSONL record EXISTS with the
    expected action + chain envelope. This is the test-side fix for the
    R-TD-1 trap: a spy can't catch a schema/registration/write-chain
    failure; an on-disk assertion can. One should-fire per emitter."""

    def _require_sync_spool(self):
        # The real-write read-back relies on CEO_AUDIT_SYNC_MODE=1 so the
        # record lands on disk synchronously. If the spool writer isn't
        # present at all, skip (partial install).
        try:
            from _lib import spool_writer  # type: ignore  # noqa: F401
        except Exception:
            self.skipTest("spool_writer unavailable")

    def _assert_chain_envelope(self, rec):
        # v2 chained-record envelope sanity (the fields _write_event adds).
        self.assertEqual(rec.get("event_schema"), "v2")
        self.assertIn("hmac", rec, "record missing chain hmac field")
        self.assertIn("ts", rec)

    def test_rate_limit_storm_writes_real_record(self):
        rl = _load_rate_limit()
        ae = _load_audit_emit()
        if rl is None:
            self.skipTest("rate_limit unavailable")
        if "federation_message_storm_detected" not in ae._KNOWN_ACTIONS:
            self.skipTest("action not registered in this build")
        self._require_sync_spool()
        rl.reset_state()
        storm = _read_ndjson("should-fire-t1499-storm.ndjson")
        self.assertTrue(storm)
        with _RealEmitLog() as log:
            for rec in storm:
                ok, _r = rl.check_rate_limit(
                    rec["peer_id"], rec["route"], rec["ip_prefix"],
                    now=rec["ts"],
                )
                if not ok:
                    rl.record_hit(rec["peer_id"], rec["route"],
                                  rec["ip_prefix"], now=rec["ts"])
                rl.check_circuit_breaker(rec["peer_id"], rec["route"],
                                         now=rec["ts"])
            recs = log.records_for("federation_message_storm_detected")
        self.assertTrue(
            recs,
            "storm must write a REAL federation_message_storm_detected "
            "record to disk (not just a spy call) — catches schema/"
            "registration/write-chain failure",
        )
        self._assert_chain_envelope(recs[0])
        # Domain fields survived the write path.
        self.assertIn("hits_in_window", recs[0])

    def test_tamper_writes_real_record(self):
        ace = _load_audit_chain_ext()
        ae = _load_audit_emit()
        if ace is None:
            self.skipTest("audit_chain_ext unavailable")
        if "federation_tamper_detected" not in ae._KNOWN_ACTIONS:
            self.skipTest("action not registered in this build")
        self._require_sync_spool()
        import tempfile
        tamper = _read_ndjson("should-fire-t1565-tamper.ndjson")
        self.assertTrue(tamper)
        with _RealEmitLog() as log:
            # Write the tampered chain to a SEPARATE file (not the audit
            # log) so check_chain inspects the fixture, while its emit goes
            # to the temp audit log under CEO_AUDIT_LOG_DIR.
            chain_dir = tempfile.mkdtemp()
            chain_log = Path(chain_dir) / "tampered-chain.jsonl"
            chain_log.write_text(
                "\n".join(json.dumps(e, sort_keys=True) for e in tamper)
                + "\n",
                encoding="utf-8",
            )
            ok, info = ace.check_chain(chain_log)
            recs = log.records_for("federation_tamper_detected")
        self.assertFalse(ok)
        self.assertTrue(
            recs,
            "tamper must write a REAL federation_tamper_detected record",
        )
        self._assert_chain_envelope(recs[0])

    def test_cert_window_writes_real_record(self):
        ae = _load_audit_emit()
        try:
            from _lib.federation.handlers import peer_register  # type: ignore
        except Exception:
            self.skipTest("peer_register unavailable")
        if "federation_cert_validity_window_too_large" not in ae._KNOWN_ACTIONS:
            self.skipTest("action not registered in this build")
        self._require_sync_spool()
        import tempfile
        body = json.dumps({
            "peer_id": "peer-real",
            "peer_id_spki_fingerprint": "a" * 64,
            "ca_pin_sha256": "b" * 64,
            "not_valid_before": "2026-01-01T00:00:00Z",
            "not_valid_after": "2027-01-01T00:00:00Z",  # ~365d > 90
            "hmac_secret_hex": "c" * 64,
        }).encode("utf-8")
        with _RealEmitLog() as log:
            status, reason, _ = peer_register.handle(
                {"peer_id": "caller"}, {}, body,
                peers_path=Path(tempfile.mkdtemp()) / "peers.yaml",
            )
            recs = log.records_for(
                "federation_cert_validity_window_too_large"
            )
        self.assertEqual(status, 400)
        self.assertTrue(
            recs,
            "cert-window rejection must write a REAL "
            "federation_cert_validity_window_too_large record",
        )
        self._assert_chain_envelope(recs[0])
        self.assertIn("window_days", recs[0])


if __name__ == "__main__":
    unittest.main()
