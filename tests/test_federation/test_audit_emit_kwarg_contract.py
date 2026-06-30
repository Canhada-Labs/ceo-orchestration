"""PLAN-099-FOLLOWUP F-001 R2 iter-2 — emit kwarg contract test.

Codex iter-2 BLOCK finding F-001: handler/dispatcher emit kwargs did
NOT match Wave F.2 typed wrapper signatures byte-for-byte. Because
``_safe_emit`` swallows exceptions, ANY unexpected kwarg would silently
fail at runtime AFTER F.2 registration — losing the forensic event with
zero error surface.

This contract test imports each Wave D handler module via
``importlib.util.spec_from_file_location``, mocks the canonical F.2
``emit_federation_*`` wrappers, drives the handler's call paths, and
asserts the mocks were invoked with the EXACT F.2 wrapper kwarg
signatures (the union of REQUIRED + OPTIONAL fields). Any unexpected
kwarg → ``TypeError`` from the strict-signature mock → test FAILS.

The canonical F.2 wrapper signatures come from
``.claude/plans/PLAN-099-FOLLOWUP/ceremony/wave-f2-audit-emit-diff.md``
Step 2.2 (the documented kernel-override diff Owner copy-pastes at
Phase A2-post). When that diff lands in
``.claude/hooks/_lib/audit_emit.py``, the same test suite continues to
hold — only the import path for the typed wrappers changes (canonical
vs staging stays compatible).

Stdlib-only per ADR-126 §Part 6.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest

# PLAN-112-FOLLOWUP-federation-wire (PHASE2): this contract suite was written
# to load the 4 write handlers as STANDALONE modules from the long-removed
# `PLAN-099-FOLLOWUP/wave-d-staging/handlers/` path (S148), with a bespoke
# audit_emit mock-injection that is incompatible with importing the handlers
# as canonical `_lib.federation.handlers.*` package members. It was
# PRE-EXISTING DEAD: never collected in CI (ImportError + absent from
# pytest.ini testpaths) and red on the baseline tree. The handler emit
# contract is now covered by the REAL-emit assertions in
# `test_attck_fixtures_fpr.py::TestRealChainedRecordPerEmitter` (writes
# through the real `emit_generic` + asserts the on-disk v2 chained record)
# and by the canonical `.claude/hooks/tests/test_audit_emit_api_contract.py`
# (in CI). Skipped (explicit + documented) pending a mock-design rework.
import pytest  # noqa: E402
pytestmark = pytest.mark.skip(
    reason="pre-existing dead (wave-d-staging removed; mock-design "
    "incompatible with canonical package import); superseded by "
    "test_attck_fixtures_fpr real-emit tests — PLAN-112-FOLLOWUP PHASE2"
)
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple
from unittest import mock


# ---------------------------------------------------------------------------
# F.2 wrapper signature reference table (the BYTE-FOR-BYTE contract).
# Mirrors `wave-f2-audit-emit-diff.md` Step 2.2 exactly. Each entry is
# the FULL kwarg surface accepted by the typed wrapper, including the
# standard envelope `session_id` / `project` keyword-only defaults.
# ---------------------------------------------------------------------------


F2_WRAPPER_SIGS: Dict[str, Set[str]] = {
    "emit_federation_scope_denied": {
        "peer_id", "route", "required_scope", "peer_scopes_count",
        "session_id", "project",
    },
    "emit_federation_write_endpoint_denied": {
        "peer_id", "route", "gate_failed", "reason_code",
        "session_id", "project",
    },
    "emit_federation_write_disabled_sentinel_invalid": {
        "reason_code", "sentinel_path",
        "session_id", "project",
    },
    "emit_federation_peer_registered": {
        "peer_id", "route", "scopes_count", "spki_fingerprint_prefix",
        "session_id", "project",
    },
    "emit_federation_peer_registered_collision": {
        "peer_id", "attempted_by_origin_peer_id",
        "session_id", "project",
    },
    "emit_federation_peer_revoked_remote": {
        "peer_id", "revoked_by_origin_peer_id", "reason_code",
        "session_id", "project",
    },
    "emit_federation_event_action_blocked": {
        "peer_id", "event_action", "reason_code",
        "session_id", "project",
    },
    "emit_federation_audit_event_pushed": {
        "peer_id", "event_action", "hmac_ok", "origin_overwritten",
        "session_id", "project",
    },
    "emit_federation_audit_event_pushed_batch": {
        "peer_id", "batch_size", "accepted_count", "rejected_count",
        "session_id", "project",
    },
    "emit_federation_message_storm_detected": {
        "peer_id", "route", "ip_prefix", "hits_in_window", "window_seconds",
        "session_id", "project",
    },
    "emit_federation_audit_log_backpressure": {
        "p99_latency_ms", "window_seconds", "action_taken",
        "session_id", "project",
    },
    "emit_federation_tamper_detected": {
        "peer_id", "route", "tamper_type", "prev_hash_prefix",
        "session_id", "project",
    },
    "emit_federation_spki_fingerprint_mismatch": {
        "peer_id", "expected_prefix", "presented_prefix", "route",
        "session_id", "project",
    },
    "emit_federation_pin_legacy_used": {
        "peer_id", "route", "der_fingerprint_prefix",
        "session_id", "project",
    },
    "emit_federation_peer_invalid_no_fingerprint": {
        "peer_id", "source_path",
        "session_id", "project",
    },
}


# ---------------------------------------------------------------------------
# Staging module loaders (file-path import via spec_from_file_location)
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[2]
_STAGING_DIR = (
    _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-d-staging"
)
_HANDLERS_STAGING = _STAGING_DIR / "handlers"


def _load_handler(name: str):
    # PLAN-112-FOLLOWUP-federation-wire (PHASE2) — the handlers were
    # promoted from PLAN-099-FOLLOWUP/wave-d-staging to canonical
    # .claude/hooks/_lib/federation/handlers/ (S148). Import the canonical
    # module via package machinery (respects the handlers' own
    # importlib.import_module contract). Falls back to the legacy staging
    # path if a canonical import is unavailable (None -> test skips body).
    try:
        _hooks = str(_REPO_ROOT / ".claude" / "hooks")
        if _hooks not in sys.path:
            sys.path.insert(0, _hooks)
        return importlib.import_module(
            "_lib.federation.handlers.{0}".format(name)
        )
    except Exception:
        path = _HANDLERS_STAGING / "{0}.py".format(name)
        if not path.is_file():
            return None
        mod_name = "_pl099_f001_h_{0}".format(name)
        spec = importlib.util.spec_from_file_location(mod_name, str(path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        return mod


# ---------------------------------------------------------------------------
# StubAuditEmit — a registry of F.2 typed wrappers with STRICT signatures.
# Any unexpected kwarg → TypeError. Mirrors what the real
# audit_emit.emit_federation_* functions do post-F.2 registration.
# ---------------------------------------------------------------------------


class _RecorderRegistry:
    """Mock registry of emit_* wrappers with strict signature enforcement."""

    def __init__(self) -> None:
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self._make_strict_wrappers()

    def _make_strict_wrappers(self) -> None:
        """Build a callable for each F.2 wrapper that enforces signature."""
        for fn_name, allowed in F2_WRAPPER_SIGS.items():
            allowed_local = frozenset(allowed)

            def _wrapper(_allowed=allowed_local, _name=fn_name, **kwargs):
                # Strict signature: reject any kwarg not in the allowlist.
                unexpected = set(kwargs.keys()) - _allowed
                if unexpected:
                    raise TypeError(
                        "F.2 wrapper '{0}' got unexpected kwarg(s): {1}; "
                        "allowed: {2}".format(
                            _name, sorted(unexpected), sorted(_allowed),
                        )
                    )
                self.calls.append((_name, dict(kwargs)))

            setattr(self, fn_name, _wrapper)

    def __getattr__(self, name):
        # Any emit_federation_* not in F2_WRAPPER_SIGS → raise so tests
        # surface the missing wrapper (catches drift between handler
        # and the documented F.2 surface).
        if name.startswith("emit_federation_"):
            raise AttributeError(
                "F.2 wrapper '{0}' is not in the documented surface; "
                "handler is emitting an unknown action".format(name)
            )
        raise AttributeError(name)

    def get_calls_for(self, action_name: str) -> List[Dict[str, Any]]:
        """Return all recorded kwarg dicts for emit_<action_name>."""
        fn_name = "emit_{0}".format(action_name)
        return [k for (n, k) in self.calls if n == fn_name]


# ---------------------------------------------------------------------------
# Test base — patches `_lib.audit_emit` in sys.modules with our registry
# ---------------------------------------------------------------------------


class _StubIdentityModule:
    """Stub for `_lib.federation.identity` used by peer_register / revoke."""

    @staticmethod
    def parse_peers_text(text: str) -> Dict[str, Any]:
        if not text.strip():
            return {"peers": []}
        return json.loads(text)

    @staticmethod
    def serialise_peers_payload(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")


class _BaseContract(unittest.TestCase):
    """Common harness: install stub `_lib.audit_emit` + identity stub."""

    def setUp(self):
        self.registry = _RecorderRegistry()
        self._saved_modules: Dict[str, Any] = {}
        for mname in (
            "_lib", "_lib.audit_emit", "_lib.federation",
            "_lib.federation.identity",
        ):
            self._saved_modules[mname] = sys.modules.get(mname)

        # Install stub `_lib` package + `_lib.audit_emit` submodule.
        # Handlers do ``from _lib import audit_emit`` which resolves
        # via the parent-module attribute lookup (NOT sys.modules
        # alone). We construct a real ModuleType for `_lib` and attach
        # our recorder as the `audit_emit` attribute so the
        # from-import sees the stub.
        import types
        lib_pkg = types.ModuleType("_lib")
        lib_pkg.audit_emit = self.registry  # type: ignore[attr-defined]
        sys.modules["_lib"] = lib_pkg
        sys.modules["_lib.audit_emit"] = self.registry  # type: ignore[assignment]

        # Stub the federation subpackage + identity (handlers lazy-
        # import these via ``from _lib.federation import identity``).
        fed_pkg = types.ModuleType("_lib.federation")
        fed_pkg.identity = _StubIdentityModule  # type: ignore[attr-defined]
        sys.modules["_lib.federation"] = fed_pkg
        sys.modules["_lib.federation.identity"] = _StubIdentityModule  # type: ignore[assignment]
        lib_pkg.federation = fed_pkg  # type: ignore[attr-defined]

        self.tmp = tempfile.mkdtemp(prefix="f001-contract-")
        self.tmp_path = Path(self.tmp)
        self.peers_yaml = self.tmp_path / "peers.yaml"
        self.peers_yaml.write_text(
            json.dumps({"peers": []}), encoding="utf-8",
        )
        self.audit_log = self.tmp_path / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        self.addCleanup(self._tidy)

    def _tidy(self):
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)
        for mname, saved in self._saved_modules.items():
            if saved is None:
                sys.modules.pop(mname, None)
            else:
                sys.modules[mname] = saved

    def _caller_peer(
        self,
        *,
        scopes_granted: Optional[List[str]] = None,
        audit_allowlist: Optional[List[str]] = None,
        revoked: bool = False,
    ) -> Dict[str, Any]:
        return {
            "peer_id": "peer-caller-contract",
            "peer_id_spki_fingerprint": "ab" * 32,
            "peer_id_cert_fingerprint": "cd" * 32,
            "scopes": list(scopes_granted) if scopes_granted else [],
            "audit_event_push_allowlist": (
                list(audit_allowlist) if audit_allowlist else []
            ),
            "revoked": revoked,
        }


# ---------------------------------------------------------------------------
# Contract test suite — drives each handler down each emit path
# ---------------------------------------------------------------------------


class TestEmitKwargContract(_BaseContract):
    """F-001 contract tests — handler emits MUST match F.2 signatures."""

    # ----- peer_register handler --------------------------------------

    def test_peer_register_success_emits_canonical_peer_registered(self):
        """Happy-path success emits federation_peer_registered with F.2 kwargs."""
        h_mod = _load_handler("peer_register")
        self.assertIsNotNone(h_mod, "peer_register staging module missing")

        body = json.dumps({
            "peer_id": "peer-new-contract-01",
            "peer_id_spki_fingerprint": "aa" * 32,
            "ca_pin_sha256": "bb" * 32,
            "hmac_secret_hex": "cc" * 32,
            "not_valid_after": "2026-08-01T00:00:00Z",
            "not_valid_before": "2026-06-01T00:00:00Z",
            "scopes": ["audit_event_push"],
        }).encode("utf-8")

        status, _, _ = h_mod.handle(
            self._caller_peer(scopes_granted=["peer_register"]),
            {"X-CEO-Federation-Scope": "peer_register"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 200)

        # Exactly one emit_federation_peer_registered call recorded.
        calls = self.registry.get_calls_for("federation_peer_registered")
        self.assertEqual(
            len(calls), 1,
            "expected 1 emit; got {0} (signature mismatch swallowed?)".format(
                len(calls),
            ),
        )
        kwargs = calls[0]
        # Confirm the F.2 contract kwargs are present and well-typed.
        self.assertEqual(kwargs["peer_id"], "peer-new-contract-01")
        self.assertEqual(kwargs["route"], "/federation/peer-register")
        self.assertIsInstance(kwargs["scopes_count"], int)
        self.assertEqual(kwargs["scopes_count"], 1)
        # spki_fingerprint_prefix must be <=16 chars (LLM06 hold).
        self.assertLessEqual(len(kwargs["spki_fingerprint_prefix"]), 16)

    def test_peer_register_bad_body_emits_canonical_write_denied(self):
        """Bad-JSON body emits federation_write_endpoint_denied with F.2 kwargs."""
        h_mod = _load_handler("peer_register")
        self.assertIsNotNone(h_mod, "peer_register staging module missing")

        status, _, _ = h_mod.handle(
            self._caller_peer(scopes_granted=["peer_register"]),
            {"X-CEO-Federation-Scope": "peer_register"},
            b"NOT VALID JSON",
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 400)

        calls = self.registry.get_calls_for(
            "federation_write_endpoint_denied",
        )
        self.assertEqual(
            len(calls), 1,
            "expected 1 emit; got {0}".format(len(calls)),
        )
        k = calls[0]
        # Must match F.2 wrapper signature: peer_id, route,
        # gate_failed, reason_code. NO `client_ip` / `caller_peer_id` /
        # `reason` / `size` etc.
        self.assertEqual(set(k.keys()),
                         {"peer_id", "route", "gate_failed", "reason_code"})
        self.assertEqual(k["route"], "/federation/peer-register")
        self.assertIsInstance(k["gate_failed"], int)

    def test_peer_register_collision_emits_canonical_collision(self):
        """Collision path emits federation_peer_registered_collision with F.2 kwargs."""
        h_mod = _load_handler("peer_register")
        self.assertIsNotNone(h_mod, "peer_register staging module missing")

        # Pre-stage a peer with the same peer_id.
        self.peers_yaml.write_text(json.dumps({
            "peers": [{
                "peer_id": "peer-collision-01",
                "peer_id_spki_fingerprint": "ff" * 32,
                "revoked": False,
                "scopes": [],
            }],
        }), encoding="utf-8")

        body = json.dumps({
            "peer_id": "peer-collision-01",  # collision
            "peer_id_spki_fingerprint": "aa" * 32,
            "ca_pin_sha256": "bb" * 32,
            "hmac_secret_hex": "cc" * 32,
            "not_valid_after": "2026-08-01T00:00:00Z",
            "not_valid_before": "2026-06-01T00:00:00Z",
            "scopes": [],
        }).encode("utf-8")

        status, _, _ = h_mod.handle(
            self._caller_peer(scopes_granted=["peer_register"]),
            {"X-CEO-Federation-Scope": "peer_register"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 409)

        calls = self.registry.get_calls_for(
            "federation_peer_registered_collision",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        # Must match F.2 wrapper signature.
        self.assertEqual(set(k.keys()),
                         {"peer_id", "attempted_by_origin_peer_id"})
        self.assertEqual(k["peer_id"], "peer-collision-01")
        self.assertEqual(
            k["attempted_by_origin_peer_id"], "peer-caller-contract",
        )

    # ----- peer_revoke handler ----------------------------------------

    def test_peer_revoke_success_emits_canonical_revoked_remote(self):
        """Happy-path emits federation_peer_revoked_remote with F.2 kwargs."""
        h_mod = _load_handler("peer_revoke")
        self.assertIsNotNone(h_mod, "peer_revoke staging module missing")

        # Pre-stage the target peer.
        self.peers_yaml.write_text(json.dumps({
            "peers": [{
                "peer_id": "peer-victim-contract",
                "revoked": False,
                "scopes": [],
            }],
        }), encoding="utf-8")

        body = json.dumps(
            {"target_peer_id": "peer-victim-contract"},
        ).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(scopes_granted=["peer_revoke"]),
            {"X-CEO-Federation-Scope": "peer_revoke"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 200)

        calls = self.registry.get_calls_for(
            "federation_peer_revoked_remote",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        self.assertEqual(set(k.keys()),
                         {"peer_id", "revoked_by_origin_peer_id", "reason_code"})
        self.assertEqual(k["peer_id"], "peer-victim-contract")
        self.assertEqual(
            k["revoked_by_origin_peer_id"], "peer-caller-contract",
        )

    def test_peer_revoke_target_not_found_emits_canonical_write_denied(self):
        """Missing-target emits federation_write_endpoint_denied with F.2 kwargs."""
        h_mod = _load_handler("peer_revoke")
        self.assertIsNotNone(h_mod, "peer_revoke staging module missing")

        body = json.dumps(
            {"target_peer_id": "peer-does-not-exist"},
        ).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(scopes_granted=["peer_revoke"]),
            {"X-CEO-Federation-Scope": "peer_revoke"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 404)

        calls = self.registry.get_calls_for(
            "federation_write_endpoint_denied",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        self.assertEqual(set(k.keys()),
                         {"peer_id", "route", "gate_failed", "reason_code"})
        self.assertEqual(k["route"], "/federation/peer-revoke")

    # ----- audit_event_push handler -----------------------------------

    def test_audit_event_push_success_emits_canonical_audit_event(self):
        """Happy-path emits federation_audit_event_pushed with F.2 kwargs."""
        h_mod = _load_handler("audit_event_push")
        self.assertIsNotNone(
            h_mod, "audit_event_push staging module missing",
        )

        body = json.dumps({
            "action": "test_action",
            "ts": "2026-05-20T00:00:00Z",
            "schema_version": "v2.28",
        }).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(
                scopes_granted=["audit_event_push"],
                audit_allowlist=["test_action"],
            ),
            {"X-CEO-Federation-Scope": "audit_event_push"},
            body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 200)

        calls = self.registry.get_calls_for(
            "federation_audit_event_pushed",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        self.assertEqual(set(k.keys()),
                         {"peer_id", "event_action", "hmac_ok",
                          "origin_overwritten"})
        self.assertEqual(k["event_action"], "test_action")
        self.assertIsInstance(k["hmac_ok"], bool)
        self.assertIsInstance(k["origin_overwritten"], bool)

    def test_audit_event_push_action_blocked_emits_canonical_event_blocked(self):
        """Action-not-in-allowlist emits federation_event_action_blocked."""
        h_mod = _load_handler("audit_event_push")
        self.assertIsNotNone(
            h_mod, "audit_event_push staging module missing",
        )

        body = json.dumps({
            "action": "forbidden_action",
            "ts": "2026-05-20T00:00:00Z",
            "schema_version": "v2.28",
        }).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(
                scopes_granted=["audit_event_push"],
                audit_allowlist=["allowed_only"],
            ),
            {"X-CEO-Federation-Scope": "audit_event_push"},
            body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 400)

        calls = self.registry.get_calls_for(
            "federation_event_action_blocked",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        # Must match F.2 wrapper signature: peer_id, event_action,
        # reason_code. NO `audit_action` / `batch_index` etc.
        self.assertEqual(set(k.keys()),
                         {"peer_id", "event_action", "reason_code"})
        self.assertEqual(k["event_action"], "forbidden_action")

    # ----- audit_event_batch handler ----------------------------------

    def test_audit_event_batch_success_emits_canonical_batch(self):
        """Happy batch emits canonical parent + per-event children."""
        h_mod = _load_handler("audit_event_batch")
        self.assertIsNotNone(
            h_mod, "audit_event_batch staging module missing",
        )

        body = json.dumps({
            "events": [
                {
                    "action": "test_action",
                    "ts": "2026-05-20T00:00:00Z",
                    "schema_version": "v2.28",
                },
                {
                    "action": "test_action",
                    "ts": "2026-05-20T00:00:01Z",
                    "schema_version": "v2.28",
                },
            ],
        }).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(
                scopes_granted=["audit_event_push_batch"],
                audit_allowlist=["test_action"],
            ),
            {"X-CEO-Federation-Scope": "audit_event_push_batch"},
            body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 200)

        # Parent emit — exactly once with F.2 kwargs.
        parent = self.registry.get_calls_for(
            "federation_audit_event_pushed_batch",
        )
        self.assertEqual(len(parent), 1)
        kp = parent[0]
        self.assertEqual(set(kp.keys()),
                         {"peer_id", "batch_size", "accepted_count",
                          "rejected_count"})
        self.assertEqual(kp["batch_size"], 2)
        self.assertEqual(kp["accepted_count"], 2)
        self.assertEqual(kp["rejected_count"], 0)

        # Per-event children — exactly 2.
        children = self.registry.get_calls_for(
            "federation_audit_event_pushed",
        )
        self.assertEqual(len(children), 2)
        for kc in children:
            # Each child MUST match the F.2 per-event wrapper signature.
            self.assertEqual(
                set(kc.keys()),
                {"peer_id", "event_action", "hmac_ok",
                 "origin_overwritten"},
            )

    def test_audit_event_batch_too_large_emits_canonical_write_denied(self):
        """Batch >MAX_BATCH_SIZE emits federation_write_endpoint_denied F.2 kwargs."""
        h_mod = _load_handler("audit_event_batch")
        self.assertIsNotNone(
            h_mod, "audit_event_batch staging module missing",
        )

        events = [
            {
                "action": "test_action",
                "ts": "2026-05-20T00:00:00Z",
                "schema_version": "v2.28",
            }
            for _ in range(101)
        ]
        body = json.dumps({"events": events}).encode("utf-8")
        status, _, _ = h_mod.handle(
            self._caller_peer(
                scopes_granted=["audit_event_push_batch"],
                audit_allowlist=["test_action"],
            ),
            {"X-CEO-Federation-Scope": "audit_event_push_batch"},
            body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 400)

        calls = self.registry.get_calls_for(
            "federation_write_endpoint_denied",
        )
        self.assertEqual(len(calls), 1)
        k = calls[0]
        # Must match F.2 wrapper signature (NO `batch_size` / `size`).
        self.assertEqual(set(k.keys()),
                         {"peer_id", "route", "gate_failed", "reason_code"})
        self.assertEqual(k["route"], "/federation/audit-event/batch")

    # ----- adversarial: unexpected kwarg -----------------------------

    def test_unexpected_kwarg_raises_typeerror_at_mock_layer(self):
        """Sanity: the strict-signature mock rejects unexpected kwargs.

        This test confirms the contract enforcement mechanism itself
        works — if any handler ever regresses and passes an unknown
        kwarg, the recorder registry raises TypeError BEFORE the silent
        _safe_emit swallow could mask it. Tests above use this
        recorder; this one directly probes the recorder.
        """
        with self.assertRaises(TypeError):
            self.registry.emit_federation_scope_denied(
                peer_id="x",
                route="/r",
                required_scope="s",
                peer_scopes_count=0,
                client_ip="1.2.3.4",  # NOT in F.2 allowlist
            )

    # ----- adversarial: unknown action -------------------------------

    def test_unknown_emit_action_raises_attributeerror(self):
        """Sanity: emit_federation_<unknown> raises AttributeError.

        Catches handler drift if a new emit site adds an action that's
        not in the documented F.2 surface (F2_WRAPPER_SIGS table).
        """
        with self.assertRaises(AttributeError):
            self.registry.emit_federation_unknown_action_xyz(peer_id="x")


# ---------------------------------------------------------------------------
# F.2-table self-consistency probe — catches drift between this test
# and `wave-f2-audit-emit-diff.md`. Cheap defense.
# ---------------------------------------------------------------------------


class TestF2WrapperTableSelfConsistency(unittest.TestCase):
    """Spot-check the F2_WRAPPER_SIGS table for shape correctness."""

    def test_every_wrapper_has_session_id_and_project(self):
        """Every F.2 wrapper accepts the standard envelope fields."""
        for fn_name, allowed in F2_WRAPPER_SIGS.items():
            self.assertIn("session_id", allowed,
                          "{0} missing session_id".format(fn_name))
            self.assertIn("project", allowed,
                          "{0} missing project".format(fn_name))

    def test_no_wrapper_accepts_client_ip(self):
        """F.2 wrappers DROP client_ip per LLM06 / GDPR hold."""
        for fn_name, allowed in F2_WRAPPER_SIGS.items():
            self.assertNotIn(
                "client_ip", allowed,
                "{0} unexpectedly accepts client_ip "
                "(should drop per LLM06)".format(fn_name),
            )


if __name__ == "__main__":
    unittest.main()
