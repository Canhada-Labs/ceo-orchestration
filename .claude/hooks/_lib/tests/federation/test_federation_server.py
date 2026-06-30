"""PLAN-099 Wave A.5 — server-side primitives tests (no real mTLS handshake).

Covers the pure-function surface of :mod:`federation.server`:

- AC3 — :func:`resolve_bind_is_loopback` covers loopback / unspecified
        / LAN / hostname-resolving cases
- AC15 — method-allowlist rejection (mocked handler dispatch)
- AC17 — :class:`JointKeyRateLimiter` bucket-by-minute + prune
- AC6 — :func:`_apply_redaction_pipeline` falls back safely without
        the redact modules
- Audit-chain helpers (:mod:`federation.audit_chain`) round-trip
"""
from __future__ import annotations

import importlib.util
import sys
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / ".claude").is_dir() and (parent / "VERSION").is_file():
            return parent
    raise RuntimeError("repo root not found from " + str(cur))


_REPO_ROOT = _repo_root()
_FED_CANONICAL = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
_FED_DRAFT = _REPO_ROOT / ".claude" / "plans" / "PLAN-099" / "federation"


def _resolve(name: str) -> Path:
    canon = _FED_CANONICAL / "{0}.py".format(name)
    draft = _FED_DRAFT / "{0}.py.draft".format(name)
    if canon.exists():
        return canon
    if draft.exists():
        return draft
    raise RuntimeError("could not find " + name + ".py or " + name + ".py.draft")


def _load(name: str, p: Path):
    loader = SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


# Order matters — server.py imports identity + replay + audit_chain.
# Load helpers first under their flat-import names so server.py's
# fallback `from identity import ...` succeeds.
#
# PLAN-134 W1 (PR #15 residue E3-F2) — the flat names are SCOPED:
# leaving `replay` registered in sys.modules after import shadows the
# .claude/scripts/replay PACKAGE and breaks pytest collection of
# replay/tests when this directory is wired into pytest.ini testpaths.
# So the flat names live only (a) while the loads below execute and
# (b) while THIS module's tests run (server.py also lazy-imports
# `from replay import verify_signature` at request time, so the flat
# name must be live during test execution, not just at import).
_FLAT_NAMES = ("identity", "replay", "audit_chain")
_PRE_EXISTING = {name: sys.modules.get(name) for name in _FLAT_NAMES}


def _restore_flat_names(saved) -> None:
    for name in _FLAT_NAMES:
        prev = saved.get(name)
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev


identity = _load("identity", _resolve("identity"))
replay = _load("replay", _resolve("replay"))
audit_chain = _load("audit_chain", _resolve("audit_chain"))
server = _load("federation_server", _resolve("server"))
_restore_flat_names(_PRE_EXISTING)

_EXEC_SAVED = {}


def setUpModule() -> None:  # noqa: N802 — unittest contract
    for name, mod in zip(_FLAT_NAMES, (identity, replay, audit_chain)):
        _EXEC_SAVED[name] = sys.modules.get(name)
        sys.modules[name] = mod


def tearDownModule() -> None:  # noqa: N802 — unittest contract
    _restore_flat_names(_EXEC_SAVED)
    _EXEC_SAVED.clear()


class TestResolveBindIsLoopback(unittest.TestCase):
    """AC3 — LAN-gate scope expansion (per S129 Codex R2 P0c fold)."""

    def test_ipv4_loopback_literal(self):
        ok, _ = server.resolve_bind_is_loopback("127.0.0.1")
        self.assertTrue(ok)

    def test_ipv6_loopback_literal(self):
        ok, _ = server.resolve_bind_is_loopback("::1")
        self.assertTrue(ok)

    def test_ipv4_unspecified_rejected(self):
        ok, _ = server.resolve_bind_is_loopback("0.0.0.0")
        self.assertFalse(ok)

    def test_ipv6_unspecified_rejected(self):
        ok, _ = server.resolve_bind_is_loopback("::")
        self.assertFalse(ok)
        ok2, _ = server.resolve_bind_is_loopback("::0")
        self.assertFalse(ok2)

    def test_lan_ipv4_rejected(self):
        for lan in ("192.168.1.50", "10.0.0.1", "172.16.0.1"):
            ok, _ = server.resolve_bind_is_loopback(lan)
            self.assertFalse(ok, lan)

    def test_empty_returns_false(self):
        ok, _ = server.resolve_bind_is_loopback("")
        self.assertFalse(ok)


class TestJointKeyRateLimiter(unittest.TestCase):
    """AC17 — joint key (peer_fpr, ip) rate limit at 10/min."""

    def test_under_limit_accepts(self):
        rl = server.JointKeyRateLimiter(10)
        now = 1234567890.0
        for _ in range(10):
            self.assertTrue(rl.allow("fpr1", "127.0.0.1", now_epoch=now))

    def test_over_limit_rejects(self):
        rl = server.JointKeyRateLimiter(3)
        now = 1234567890.0
        for _ in range(3):
            self.assertTrue(rl.allow("fpr1", "127.0.0.1", now_epoch=now))
        self.assertFalse(rl.allow("fpr1", "127.0.0.1", now_epoch=now))

    def test_different_peer_isolated(self):
        rl = server.JointKeyRateLimiter(2)
        now = 1234567890.0
        self.assertTrue(rl.allow("fpr1", "127.0.0.1", now_epoch=now))
        self.assertTrue(rl.allow("fpr1", "127.0.0.1", now_epoch=now))
        self.assertFalse(rl.allow("fpr1", "127.0.0.1", now_epoch=now))
        # Different peer fpr — separate bucket.
        self.assertTrue(rl.allow("fpr2", "127.0.0.1", now_epoch=now))

    def test_different_ip_isolated(self):
        rl = server.JointKeyRateLimiter(2)
        now = 1234567890.0
        self.assertTrue(rl.allow("fpr1", "10.0.0.1", now_epoch=now))
        self.assertTrue(rl.allow("fpr1", "10.0.0.1", now_epoch=now))
        self.assertFalse(rl.allow("fpr1", "10.0.0.1", now_epoch=now))
        # Same fpr, different IP — separate bucket (joint key).
        self.assertTrue(rl.allow("fpr1", "10.0.0.2", now_epoch=now))

    def test_minute_rollover_resets(self):
        rl = server.JointKeyRateLimiter(2)
        now = 1234567890.0
        rl.allow("fpr1", "127.0.0.1", now_epoch=now)
        rl.allow("fpr1", "127.0.0.1", now_epoch=now)
        self.assertFalse(rl.allow("fpr1", "127.0.0.1", now_epoch=now))
        # 65s later — new bucket.
        later = now + 65
        self.assertTrue(rl.allow("fpr1", "127.0.0.1", now_epoch=later))


class TestApplyRedactionPipeline(unittest.TestCase):
    """AC6 — redaction pipeline (graceful fallback when modules missing)."""

    def test_empty_list_returns_empty(self):
        out = server._apply_redaction_pipeline([])
        self.assertEqual(out, [])

    def test_non_dict_entries_filtered(self):
        out = server._apply_redaction_pipeline([
            "not a dict",  # type: ignore[list-item]
            123,           # type: ignore[list-item]
            {"action": "ok"},
        ])
        # Only the dict survives.
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["action"], "ok")

    def test_well_formed_dict_passes_through_when_redactors_present(self):
        # AC6 fail-CLOSED: when _lib.redact + _lib.pii_patterns are both
        # importable, the pipeline runs and preserves shape. Inject the
        # repo's hooks dir into sys.path so the lazy import inside
        # _apply_redaction_pipeline finds them.
        hooks_dir = _REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        evt = {"action": "test", "ts": 12345, "session_id": "abc"}
        out = server._apply_redaction_pipeline([evt])
        if not out:
            # Modules unavailable in this env → fail-CLOSED is the
            # expected behaviour (cross-machine leak prevention).
            self.assertEqual(out, [])
            return
        self.assertEqual(len(out), 1)
        # Pipeline preserves the action + scalar keys.
        self.assertEqual(out[0]["action"], "test")

    def test_fail_closed_when_redactors_missing(self):
        # AC6 fail-CLOSED — when modules are NOT importable, the
        # pipeline returns [] (refuses to leak unredacted content
        # cross-machine, per Codex R2 iter-1 P0#2 fold).
        # We simulate the missing case by temporarily breaking sys.modules
        # for the lazy import path.
        evt = {"action": "test", "ts": 12345}
        sentinels = {}
        # Hide both modules + the package itself from import lookups.
        for mod_name in ("_lib", "_lib.redact", "_lib.pii_patterns"):
            sentinels[mod_name] = sys.modules.pop(mod_name, None)
        # Also remove the hooks dir from sys.path so a re-import can't
        # find them.
        hooks_dir = _REPO_ROOT / ".claude" / "hooks"
        prev_path = list(sys.path)
        sys.path[:] = [p for p in sys.path if Path(p).resolve() != hooks_dir]
        try:
            out = server._apply_redaction_pipeline([evt])
            self.assertEqual(out, [], "fail-CLOSED contract — expected [] when redactors missing")
        finally:
            sys.path[:] = prev_path
            for name, mod in sentinels.items():
                if mod is not None:
                    sys.modules[name] = mod


class TestAuditChainHelpers(unittest.TestCase):
    """Wave C primitives — origin tagging + correlation propagation."""

    def test_generate_correlation_id_format(self):
        cid = audit_chain.generate_correlation_id()
        self.assertTrue(cid.startswith("fed-"))
        self.assertGreater(len(cid), 16)

    def test_tag_remote_event_adds_both_keys(self):
        ev = {"action": "rag_query_routed", "session_id": "s1"}
        out = audit_chain.tag_remote_event(
            ev,
            federation_origin="a" * 64,
            correlation_id="fed-test",
        )
        self.assertEqual(out["federation_origin"], "a" * 64)
        self.assertEqual(out["fed_correlation_id"], "fed-test")
        # Original keys preserved.
        self.assertEqual(out["action"], "rag_query_routed")

    def test_tag_remote_event_preserves_upstream_attribution(self):
        ev = {
            "action": "x",
            "federation_origin": "upstream-origin",
            "fed_correlation_id": "upstream-id",
        }
        out = audit_chain.tag_remote_event(
            ev,
            federation_origin="OUR-origin",
            correlation_id="OUR-id",
        )
        # setdefault must NOT overwrite.
        self.assertEqual(out["federation_origin"], "upstream-origin")
        self.assertEqual(out["fed_correlation_id"], "upstream-id")

    def test_tag_remote_event_lowercases_origin(self):
        ev = {"action": "x"}
        out = audit_chain.tag_remote_event(
            ev,
            federation_origin="A" * 64,
        )
        self.assertEqual(out["federation_origin"], "a" * 64)

    def test_tag_remote_event_requires_origin(self):
        with self.assertRaises(ValueError):
            audit_chain.tag_remote_event({"action": "x"}, federation_origin="")

    def test_tag_remote_event_requires_dict(self):
        with self.assertRaises(TypeError):
            audit_chain.tag_remote_event("not a dict", federation_origin="x")  # type: ignore[arg-type]

    def test_stamp_local_with_correlation(self):
        ev = {"action": "federation_connection_accepted", "peer_id": "p1"}
        out = audit_chain.stamp_local_with_correlation(ev, "fed-xyz")
        self.assertEqual(out["fed_correlation_id"], "fed-xyz")
        self.assertEqual(out["peer_id"], "p1")

    def test_stamp_local_empty_id_no_op(self):
        ev = {"action": "x"}
        out = audit_chain.stamp_local_with_correlation(ev, "")
        # No correlation stamped; copy returned unchanged.
        self.assertNotIn("fed_correlation_id", out)


class TestKillSwitchInvariants(unittest.TestCase):
    """ADR-129 §Part 8 — master kill-switch refusal."""

    def test_serve_forever_refuses_without_kill_switch(self):
        import os
        cfg = server.FederationConfig(
            bind_host="127.0.0.1",
            bind_port=0,
            cert_file=Path("/nonexistent/cert.pem"),
            key_file=Path("/nonexistent/key.pem"),
            ca_file=Path("/nonexistent/ca.pem"),
            peers_path=Path("/nonexistent/peers.yaml"),
            enabled_sentinel=Path("/nonexistent/enabled.md"),
            enabled_sentinel_asc=Path("/nonexistent/enabled.md.asc"),
            lan_enabled_sentinel=Path("/nonexistent/lan.md"),
            lan_enabled_sentinel_asc=Path("/nonexistent/lan.md.asc"),
        )
        srv = server.FederationServer(cfg)
        prev = os.environ.get("CEO_FEDERATION_ENABLED")
        try:
            os.environ["CEO_FEDERATION_ENABLED"] = "0"
            with self.assertRaises(server.FederationStartError) as ctx:
                srv.serve_forever()
            self.assertIn("kill-switch", str(ctx.exception))
        finally:
            if prev is None:
                os.environ.pop("CEO_FEDERATION_ENABLED", None)
            else:
                os.environ["CEO_FEDERATION_ENABLED"] = prev


class TestMaxCertValiditySingleSource(unittest.TestCase):
    """PLAN-113 W5 — F-5.8-mac-cert-validity-duplicate.

    ``MAX_CERT_VALIDITY_DAYS`` must live in exactly ONE place
    (``federation/__init__.py``). server.py derives it (package import
    in normal mode; sourced-by-path in the flat-import fallback) and
    must NOT carry an independent literal that can drift.
    """

    def _init_literal(self) -> int:
        """Parse the canonical literal straight out of __init__.py."""
        init_path = _FED_CANONICAL / "__init__.py"
        import re as _re
        m = _re.search(
            r"^MAX_CERT_VALIDITY_DAYS\s*=\s*(\d+)\s*$",
            init_path.read_text(encoding="utf-8"),
            _re.MULTILINE,
        )
        assert m is not None, "MAX_CERT_VALIDITY_DAYS not found in __init__.py"
        return int(m.group(1))

    def test_flat_import_value_matches_init_no_drift(self):
        # `server` is loaded flat (no `federation` package) at module top,
        # exercising the except-ImportError fallback — the exact path the
        # finding flagged as a drift risk.
        self.assertEqual(server.MAX_CERT_VALIDITY_DAYS, self._init_literal())

    def test_value_is_unchanged_90(self):
        # Behavior-preservation guard: the de-dup must not move the number.
        self.assertEqual(server.MAX_CERT_VALIDITY_DAYS, 90)

    def test_helper_sources_from_init(self):
        # The fallback helper reads the real sibling __init__.py and returns
        # its literal, ignoring the supplied default when the file is present.
        self.assertEqual(
            server._read_max_cert_validity_days_from_init(default=-1),
            self._init_literal(),
        )

    def test_helper_fail_soft_default_when_unreadable(self):
        # If the sibling file ever became unreadable the helper returns the
        # historical default rather than raising (fail-soft per CLAUDE.md).
        import unittest.mock as _mock
        with _mock.patch.object(
            server.Path, "read_text", side_effect=OSError("boom")
        ):
            self.assertEqual(
                server._read_max_cert_validity_days_from_init(default=90), 90
            )


if __name__ == "__main__":
    unittest.main()
