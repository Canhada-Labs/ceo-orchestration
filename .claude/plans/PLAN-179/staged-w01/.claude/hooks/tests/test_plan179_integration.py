#!/usr/bin/env python3
"""PLAN-179 W0/W1/W1-b — ONE hermetic end-to-end proof that the pack CURES.

## Why this module exists, separately from test_check_compaction_continuity.py

Every file in the PLAN-179 W0/W1 pack was written by an agent that could not
see the others: the hook authors, the `_lib` authors, the SPEC author. Their
individual unit suites are green, and green-per-file is exactly the evidence
shape that let the ORIGINAL defect ship — ADR-153's fires-proof (S309) had
passing unit tests for both halves while the real autocompact at 09:34Z
delivered `snapshot_outcome=scratchpad_unavailable`, `plan_id=unknown`,
`snapshot_found=false`, `pointer_count=1`. Nothing was broken in isolation;
the CROSS-FILE contract was.

So this module asserts the plan's EXIT CRITERIA as pipeline outcomes — the
same quantities the failure was measured in — rather than re-testing units:

  (1) W1 exit (a)   — PreCompact then PostCompact in a session with NO
                      `plan_transition` yields snapshot_found=true and
                      pointer_count>1  (`TestHeadlineExitCriterion`);
  (2) r1-C1         — an env-sourced session id is REFUSED, outcome stays
                      `scratchpad_unavailable`  (`TestSessionIdRefusal`);
  (3) W1-b exit (b) — SessionStart(source=compact) returns the full pinned set
                      with an EMPTY scratchpad and NO snapshot
                      (`TestPinningPrimaryChannel`);
  (4) r1-C3         — constraints and pointers are on SEPARATE budgets
                      (`TestBudgetSeparation`);
  (5) amendment 8.3 — a secret planted in the snapshot INPUT is redacted in
                      the stored blob  (`TestSnapshotRedaction`);
  (6) W1-b counters — the reinject event carries an integer `constraint_count`
                      and `pointer_count` still counts pointers only
                      (`TestReinjectCounters`);
  (+) W0 US2b       — the context-pressure instrument actually FIRES
                      (`TestContextPressureInstrumentFires`). Not a numbered
                      exit criterion, but the pack's own cross-file pass named
                      three defects of the "instrument that runs and cannot
                      fire" class in `_progress_guard` (a getattr-probe on a
                      symbol that does not exist, two field names outside the
                      deny-by-default allowlist, and a token-count bucket that
                      could never match a percent rung). An instrument that
                      cannot fire is worse than no instrument, so the cure is
                      proved by observing a real event on the wire.

## Hermeticity

`TestEnvContext` (`_lib/testing.py`) gives every test a fresh `$HOME`, a fresh
`CLAUDE_PROJECT_DIR` and a `CEO_AUDIT_LOG_*` family pointed into a per-test
tmpdir. `CEO_STATE_ROOT` is additionally pinned into that same tmpdir so the
sqlite scratchpad stores cannot resolve to the operator's real
`~/.claude/projects/.../state` even if the `$HOME` redirect were ever loosened.
`test_audit_log_is_redirected` is the positive control on that isolation: if it
fails, NOTHING else in this module may be believed, because the events being
asserted could be the operator's live ones.

## Module resolution — STAGED FIRST, pack-relative

The task this file answers is "does the PACK deliver the cure", so the modules
under test are resolved RELATIVE TO THIS FILE (`../` is the pack's hooks dir),
not from the live tree. `_pick_staged_first` still falls back to the canonical
copy when the staged file is gone, so the same file keeps working after the
Owner's ceremony lands the pack and the `staged-w01/` tree is retired — the
alternative (a hard-coded staged path) would turn into a collection error the
day the pack is deleted.

## sys.modules discipline (PLAN-118 AC-B7 + PLAN-119-FOLLOWUP WS-2)

The staged `_lib` modules (`audit_emit`, `scratchpad_lib`, `pinned_constraints`)
are bound under their canonical dotted names ONLY for the duration of a gate()
call — the hooks import `_lib.*` lazily — and restored afterwards, package
attribute included. `_AuditEmitSlotGuard` and the per-class teardown re-import
satisfy the WS-2 shadow-loader restore gate
(`.claude/scripts/check-test-audit-isolation.py`): the installing class calls
the loader helper AND restores canonical `_lib.audit_emit` in its teardown.

Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

# --------------------------------------------------------------------------
# Path resolution: the PACK is the subject; the LIVE tree supplies `_lib`
# infrastructure the pack does not ship (testing.py, state_store, redact, ...).
# --------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
# tests/ -> hooks/  (this file lives at <pack>/.claude/hooks/tests/)
_PACK_HOOKS = _THIS.parent.parent

_repo_root: Optional[Path] = None
for _parent in _THIS.parents:
    # The pack's own `.claude/` has hooks/_lib but NO plans/, so the walk
    # cannot stop inside staged-w01 by accident.
    if (_parent / ".claude" / "hooks" / "_lib").is_dir() and (
        _parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = _parent
        break
assert _repo_root is not None, "could not locate repo root from %s" % _THIS
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"


def _pick_staged_first(staged: Path, canonical: Path, marker: str) -> Path:
    """The PACK copy when it exists and carries `marker`, else the canonical.

    Staged-first is deliberate and is the opposite of the unit suite's
    canonical-first `_pick`: that file asks "does the code behave", this one
    asks "does THIS PACK deliver", and answering it from the live tree would
    silently test the pre-cure code. The canonical fallback exists only so the
    module survives the ceremony that deletes `staged-w01/`.

    The marker is checked in both positions: a path that exists but lacks the
    PLAN-179-era symbol is the pre-cure file, and selecting it would make every
    assertion below fail for the wrong reason."""
    for candidate in (staged, canonical):
        try:
            if candidate.is_file() and marker in candidate.read_text(encoding="utf-8"):
                return candidate
        except OSError:
            continue
    raise FileNotFoundError(
        "PLAN-179 subject not found in pack (%s) or canonical (%s); marker=%r"
        % (staged, canonical, marker)
    )


# Markers are W1/W1-b-era symbols: the PLAN-135 ones exist in the live tree too.
_SRC_PRE = _pick_staged_first(
    _PACK_HOOKS / "check_precompact_continuity.py",
    _LIVE_HOOKS / "check_precompact_continuity.py",
    "written_session_scope",
)
_SRC_POST = _pick_staged_first(
    _PACK_HOOKS / "check_postcompact_reinject.py",
    _LIVE_HOOKS / "check_postcompact_reinject.py",
    "_render_constraints",
)
_SRC_PIN = _pick_staged_first(
    _PACK_HOOKS / "check_compact_pinning.py",
    _LIVE_HOOKS / "check_compact_pinning.py",
    "_COMPACT_SOURCE",
)
_SRC_AE = _pick_staged_first(
    _PACK_HOOKS / "_lib" / "audit_emit.py",
    _LIVE_HOOKS / "_lib" / "audit_emit.py",
    "_CONTEXT_PRESSURE_OBSERVED_ALLOWLIST",
)
_SRC_SP = _pick_staged_first(
    _PACK_HOOKS / "_lib" / "scratchpad_lib.py",
    _LIVE_HOOKS / "_lib" / "scratchpad_lib.py",
    "open_session_scratchpad",
)
_SRC_PC = _pick_staged_first(
    _PACK_HOOKS / "_lib" / "pinned_constraints.py",
    _LIVE_HOOKS / "_lib" / "pinned_constraints.py",
    "PINNED_CONSTRAINTS",
)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # the canonical `_lib` package

import _lib  # noqa: E402 — the package whose submodule attrs we rebind
from _lib.testing import TestEnvContext  # noqa: E402

_SENTINEL = object()


def _load_hook(name: str, path: Path):
    """Load a hook under a TEST-LOCAL module name (never a `_lib.*` slot)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_staged_audit_emit():
    """Exec the pack's audit_emit WITHOUT leaving it in the canonical slot.

    PLAN-119-FOLLOWUP WS-2: the slot is only ever occupied inside
    `_bind_pack_lib()`, which restores it in a `finally`."""
    spec = importlib.util.spec_from_file_location("_lib.audit_emit", str(_SRC_AE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_pack_lib(attr_name: str, path: Path):
    """Exec a pack `_lib` submodule under its canonical dotted name, unbound.

    Its own `from _lib import ...` lines resolve against the LIVE package, so
    only the file under test is swapped — state_store / redact / filelock stay
    canonical, which is what makes the redaction proof (5) meaningful."""
    spec = importlib.util.spec_from_file_location("_lib." + attr_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_pre_hook = _load_hook("plan179_it_precompact", _SRC_PRE)
_post_hook = _load_hook("plan179_it_postcompact", _SRC_POST)
_pin_hook = _load_hook("plan179_it_compact_pinning", _SRC_PIN)
_pack_ae = _load_staged_audit_emit()
_pack_sp = _load_pack_lib("scratchpad_lib", _SRC_SP)
_pack_pc = _load_pack_lib("pinned_constraints", _SRC_PC)

_PACK_LIB_MODULES = (
    ("audit_emit", _pack_ae),
    ("scratchpad_lib", _pack_sp),
    ("pinned_constraints", _pack_pc),
)


@contextlib.contextmanager
def _bind_pack_lib():
    """Bind the pack's `_lib` submodules transiently; restore everything.

    Both `sys.modules["_lib.<name>"]` AND the `_lib` package ATTRIBUTE are
    rebound: once any earlier test in the suite has imported the live module,
    the package holds an attribute pointing at it and a bare sys.modules rebind
    would not be seen by `from _lib import <name>`. The "was absent" case must
    DELETE rather than leave a stale binding — `pinned_constraints` does not
    exist in the live tree pre-ceremony, so that is the normal case here."""
    saved = []
    for attr, mod in _PACK_LIB_MODULES:
        dotted = "_lib." + attr
        saved.append(
            (attr, dotted, sys.modules.get(dotted, _SENTINEL), getattr(_lib, attr, _SENTINEL))
        )
        sys.modules[dotted] = mod
        setattr(_lib, attr, mod)
    try:
        yield
    finally:
        for attr, dotted, saved_sm, saved_attr in reversed(saved):
            if saved_sm is _SENTINEL:
                sys.modules.pop(dotted, None)
            else:
                sys.modules[dotted] = saved_sm
            if saved_attr is _SENTINEL:
                if hasattr(_lib, attr):
                    delattr(_lib, attr)
            else:
                setattr(_lib, attr, saved_attr)


class _AuditEmitSlotGuard(TestEnvContext):
    """PLAN-119-FOLLOWUP WS-2 restore gate.

    `_load_staged_audit_emit()` runs at module import and contains the
    `spec_from_file_location("_lib.audit_emit", ...)` install form the static
    gate tracks. The gate requires the INSTALLING CLASS to call the helper and
    restore canonical in its own teardown; this class does exactly that
    (idempotent — the loader never leaves the slot occupied in the first
    place).

    PLAN-179 (Codex pair-rail finding B, `bare-testcase`): the base is
    `TestEnvContext`, not `unittest.TestCase`. `check-test-env-hygiene.py`
    flags a lone `unittest.TestCase` base because such a class runs with the
    operator's real `$HOME`, `CLAUDE_PROJECT_DIR` and `CEO_*` — and this class
    execs a module under a canonical `_lib.*` slot, so it is precisely the kind
    that must not leak. The assertion below is unchanged."""

    @classmethod
    def setUpClass(cls):
        _load_staged_audit_emit()

    @classmethod
    def tearDownClass(cls):
        importlib.import_module("_lib.audit_emit")

    def test_canonical_audit_emit_slot_is_importable(self):
        self.assertIn("_lib.audit_emit", sys.modules)


class _IntegrationBase(TestEnvContext):
    """Hermetic fixture shared by every criterion below.

    Two session ids, deliberately different in ONE respect each:

      - ``SESSION_WITH_PLAN`` has a ``plan_transition`` seeded for it, so
        ``resolve_plan_id`` succeeds and the PLAN scope is exercised;
      - ``SESSION_NO_PLAN`` has none — which is the S309-measured DOMINANT
        state, not an edge case (2 ``plan_transition`` events in 12,515 audit
        lines) — and is shaped ``session-<hex/dashes>`` because that is the
        only form ``scratchpad_lib.session_scope_id`` accepts. The shape is
        derived from the module's own regex rather than recalled
        ([[feedback-closed-sets-must-be-derived-not-recalled]])."""

    PLAN_ID = "PLAN-179"
    SESSION_WITH_PLAN = "sess-plan179-integration"
    SESSION_NO_PLAN = "session-0f1c0f6e-1111-2222-3333-444455556666"

    def setUp(self) -> None:
        super().setUp()
        # Hermeticity, belt and braces: TestEnvContext already redirects HOME
        # (which _state_root() derives from), but pinning CEO_STATE_ROOT means
        # the sqlite scratchpads cannot reach the operator's real state dir
        # even if that derivation ever changes.
        self._state_root = self._tmp_root / "state-root"
        # PLAN-179 (Codex pair-rail finding A, `env-write`): the sanctioned
        # form is `mock.patch.dict`, never `os.environ[K] = V`
        # (check-test-env-hygiene.py). The patcher is started here and stopped
        # in `tearDown` BEFORE `TestEnvContext.tearDown` restores the operator's
        # env — deliberately NOT via `addCleanup`, whose callbacks run AFTER
        # tearDown, and whose `patch.dict` unpatch does a wholesale
        # `os.environ.clear()` + restore of the IN-TEST snapshot; running it
        # last would re-pollute the just-restored real environment with a HOME
        # pointing at a deleted tmpdir.
        self._env_patcher = mock.patch.dict(
            os.environ,
            {
                "CEO_STATE_ROOT": str(self._state_root),
                "CLAUDE_SESSION_ID": self.SESSION_WITH_PLAN,
            },
        )
        self._env_patcher.start()
        os.environ.pop("CEO_COMPACTION_CONTINUITY", None)
        os.environ.pop("CEO_CONSTRAINT_PINNING", None)
        os.environ.pop("CEO_CONTEXT_PROGRESS_FLOOR_TOKENS", None)

        self._seed_plan_transition(self.SESSION_WITH_PLAN, self.PLAN_ID)
        self.plans_dir = self.project_dir / ".claude" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.write_plan_file("- [x] landed unit\n- [ ] active unit\n- [ ] later\n")
        self.cwd = str(self.project_dir)

    def tearDown(self) -> None:
        # PLAN-119-FOLLOWUP WS-2: re-assert the canonical slot before
        # TestEnvContext tears the isolated HOME/audit tree down. Idempotent —
        # `_bind_pack_lib` already restored it in its own finally.
        importlib.import_module("_lib.audit_emit")
        # PLAN-179 finding A: unpatch BEFORE super() restores the real env —
        # see the ordering note in setUp.
        self._env_patcher.stop()
        super().tearDown()

    # ---- fixture helpers -------------------------------------------------

    def write_plan_file(self, body: str) -> Path:
        target = self.plans_dir / (self.PLAN_ID + "-integration.md")
        target.write_text("# %s\n\n%s" % (self.PLAN_ID, body), encoding="utf-8")
        return target

    def _seed_plan_transition(self, session_id: str, plan_id: str) -> None:
        """Append the ONE event shape `resolve_plan_id` consumes.

        This is the whole reason the cure was needed: a `plan_transition` is
        emitted only on a status CHANGE, so a long session normally carries
        none of its own — and a long session is the only kind that compacts."""
        path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "action": "plan_transition",
                        "session_id": session_id,
                        "plan_id": plan_id,
                        "from_status": "reviewed",
                        "to_status": "executing",
                    }
                )
                + "\n"
            )

    def run_pre(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with _bind_pack_lib():
            return _pre_hook.gate(event, event.get("cwd"))

    def run_post(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with _bind_pack_lib():
            return _post_hook.gate(event)

    def run_pin(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with _bind_pack_lib():
            return _pin_hook.gate(event)

    def read_blob(self, *, plan_id: Optional[str] = None,
                  session_id: Optional[str] = None) -> Optional[bytes]:
        """Raw `compaction_continuity` value from the named SCOPE (or None)."""
        key = _pre_hook.SCRATCHPAD_KEY
        with _bind_pack_lib():
            if session_id is not None:
                with _pack_sp.open_session_scratchpad(session_id) as store:
                    return store.get(key)
            with _pack_sp.open_scratchpad(plan_id=plan_id) as store:
                return store.get(key)

    def plant_blob(self, blob: Dict[str, Any], *, plan_id: Optional[str] = None) -> None:
        """Write a snapshot blob DIRECTLY into the plan store.

        Used where the test needs a snapshot with a SHAPE the writer would not
        naturally produce (a saturated pointer set). Planting asks "given this
        snapshot, what does the reader do", which is the question the budget
        criterion is about; "can the writer be tricked" is a different question
        and is already covered by the unit suite."""
        with _bind_pack_lib():
            with _pack_sp.open_scratchpad(plan_id=plan_id or self.PLAN_ID) as store:
                store.set(
                    _pre_hook.SCRATCHPAD_KEY,
                    json.dumps(blob, ensure_ascii=False, sort_keys=True),
                )

    def events(self, action: str) -> List[Dict[str, Any]]:
        path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        out: List[Dict[str, Any]] = []
        if not path.is_file():
            return out
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("action") == action:
                out.append(ev)
        return out

    def one_event(self, action: str) -> Dict[str, Any]:
        evs = self.events(action)
        self.assertEqual(
            len(evs), 1,
            "expected exactly one %r event, got %d — a hook that emits zero is "
            "a dead instrument and one that emits many is a wire flood"
            % (action, len(evs)),
        )
        return evs[0]

    def constraint_block(self) -> List[str]:
        """The pinned block as its OWNER renders it (never restated here)."""
        with _bind_pack_lib():
            return list(_pack_pc.render_pinned_block())


class TestHermeticity(_IntegrationBase):
    """Positive control on the isolation every other assertion rests on."""

    def test_audit_log_is_redirected(self):
        # If this fails, no event asserted anywhere in this module can be
        # attributed to the code under test — they could be the operator's.
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"]).resolve()
        self.assertTrue(
            str(log_path).startswith(str(self._tmp_root.resolve())),
            "audit log %s is not inside the per-test tmpdir %s" % (log_path, self._tmp_root),
        )
        # The operator's REAL home is the one snapshotted BEFORE setUp
        # redirected $HOME. `Path.home()` would be useless here: it reads the
        # already-redirected $HOME, so it names the tmpdir and the check would
        # pass by construction — a vacuous control, which is the failure mode
        # this whole class exists to rule out.
        original_home = self._env_snapshot.get("HOME")
        if original_home:
            self.assertFalse(
                str(log_path).startswith(str(Path(original_home).resolve())),
                "the audit log resolves under the operator's real HOME (%s)"
                % original_home,
            )

    def test_state_root_is_redirected(self):
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                      "trigger": "manual"})
        # The store file must materialize inside the tmp state root, nowhere else.
        created = list(self._state_root.rglob("*.sqlite"))
        self.assertTrue(
            created,
            "no sqlite store under CEO_STATE_ROOT — either the write did not "
            "happen or it landed outside the isolated tree",
        )

    def test_subject_modules_come_from_the_pack(self):
        # Names the file each assertion is actually about, so a future reader
        # never has to guess whether this module tested the pack or the live
        # tree. Informational when the pack is gone (post-ceremony fallback).
        for src in (_SRC_PRE, _SRC_POST, _SRC_PIN, _SRC_AE, _SRC_SP, _SRC_PC):
            self.assertTrue(src.is_file(), "subject vanished: %s" % src)


class TestHeadlineExitCriterion(_IntegrationBase):
    """(1) PLAN-179 W1 exit criterion (a) — the ADR-153 fires-proof, cured.

    THE MEASURED FAILURE (S309, real autocompact 2026-08-16 09:34Z), kept here
    verbatim so a future reader can see exactly what changed:

        plan_id           = unknown
        snapshot_outcome  = scratchpad_unavailable
        snapshot_found    = false
        pointer_count     = 1

    Same scenario, no weakening: a session that never emitted a
    `plan_transition`, which S309's census showed is the DOMINANT state (2 such
    events in 12,515 audit lines) and is anti-correlated with the use case —
    only long sessions compact, and long sessions rarely transition a plan.
    `plan_id` is STILL `unknown` below (r1-C1 forbids overloading it with the
    session scope); everything else flips."""

    def test_no_plan_transition_pipeline_delivers_continuity(self):
        event_pre = {
            "cwd": self.cwd,
            "session_id": self.SESSION_NO_PLAN,
            "trigger": "auto",
        }
        self.assertEqual(self.run_pre(event_pre), {},
                         "PreCompact has no governance output channel")

        snap_ev = self.one_event("compaction_continuity_snapshot")
        # WAS: scratchpad_unavailable (the write was dropped on the floor).
        self.assertEqual(
            snap_ev["snapshot_outcome"], "written_session_scope",
            "the snapshot was not written to the session scope — the writer "
            "half of the ADR-153 cure did not take",
        )
        # WAS: unknown, and it STILL IS: the session scope must never be
        # smuggled through plan_id (amendment r1-C1).
        self.assertEqual(snap_ev["plan_id"], "unknown")

        out = self.run_post({"cwd": self.cwd, "session_id": self.SESSION_NO_PLAN})
        hso = out.get("hookSpecificOutput")
        self.assertIsNotNone(hso, "PostCompact produced no additionalContext")
        self.assertEqual(hso["hookEventName"], "PostCompact")

        re_ev = self.one_event("compaction_context_reinjected")
        # WAS: false.
        self.assertTrue(
            re_ev["snapshot_found"],
            "the session-scoped snapshot was written but not read back — the "
            "reader is still plan-scope only, i.e. the measured S309 failure",
        )
        # WAS: 1 (the durable Gate-1 reminder and nothing else).
        self.assertGreater(
            re_ev["pointer_count"], 1,
            "pointer_count is still 1 — the reinject carries only the durable "
            "reminder, so the cure delivered nothing",
        )
        self.assertEqual(re_ev["plan_id"], "unknown")

        # And the payload really names the store the snapshot is IN. The
        # cross-file pass fixed a pointer that announced every session-scope
        # snapshot as living in "this plan's scratchpad" — a store that by
        # definition has no entry for it.
        ctx = hso["additionalContext"]
        self.assertIn(_post_hook.SCRATCHPAD_KEY, ctx)
        self.assertIn("SESSION's scratchpad", ctx,
                      "the snapshot pointer names the wrong store")

    def test_blob_is_stamped_with_its_scope(self):
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_NO_PLAN,
                      "trigger": "manual"})
        raw = self.read_blob(session_id=self.SESSION_NO_PLAN)
        self.assertIsNotNone(raw, "session-scope snapshot is not on disk")
        blob = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        # `scope_kind` is the field the reader keys on; it comes from
        # scratchpad_lib's enum owner (stamp_scope_kind), not a literal.
        self.assertEqual(blob["scope_kind"], _pack_sp.SCOPE_KIND_SESSION)
        self.assertEqual(blob["plan_id"], "unknown")


class TestSessionIdRefusal(_IntegrationBase):
    """(2) Amendment r1-C1 — the REFUSAL is the security property.

    `CLAUDE_SESSION_ID` is set to a WELL-FORMED session id, so the only thing
    standing between it and a successful session-scope write is the provenance
    rule itself; the hook input carries no session id at all. An env var is
    agent-spoofable — any agent that can run a subshell can
    `export CLAUDE_SESSION_ID=<victim>` before a hook fires and steer the
    continuity write into a scope it chose (the same threat consensus M2 cited
    when it banned `CEO_CURRENT_PLAN`). Refusal must report
    `scratchpad_unavailable`, never a fabricated success."""

    def test_env_sourced_session_id_is_refused(self):
        # PLAN-179 (Codex pair-rail finding A): `mock.patch.dict` replaces the
        # direct `os.environ[...] =` write. The variable is STILL set, and to
        # the SAME well-formed value — the refusal is only meaningful while a
        # spoofable, syntactically-valid id is sitting in the environment.
        with mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": self.SESSION_NO_PLAN}
        ):
            out = self.run_pre({"cwd": self.cwd, "trigger": "manual"})
            self.assertEqual(out, {})

            ev = self.one_event("compaction_continuity_snapshot")
            self.assertEqual(ev["plan_id"], "unknown")
            self.assertEqual(
                ev["snapshot_outcome"], "scratchpad_unavailable",
                "an env-sourced session id was accepted as a write scope (r1-C1)",
            )
            # Positive control: without it this test would pass just as happily
            # if the write had failed for some unrelated reason.
            self.assertIsNone(
                self.read_blob(session_id=self.SESSION_NO_PLAN),
                "something WAS written under the env-named scope",
            )

    def test_hook_input_session_id_is_still_accepted(self):
        """The negative control for the refusal above.

        Same env var, same everything — except the id now ALSO arrives on the
        hook input. If this were red the refusal test would be vacuous (it
        would pass because nothing ever writes, not because provenance is
        enforced)."""
        # PLAN-179 finding A: same env var, same value, sanctioned form.
        with mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": self.SESSION_NO_PLAN}
        ):
            self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_NO_PLAN,
                          "trigger": "manual"})
            ev = self.one_event("compaction_continuity_snapshot")
            self.assertEqual(ev["snapshot_outcome"], "written_session_scope")
            self.assertIsNotNone(self.read_blob(session_id=self.SESSION_NO_PLAN))


class TestPinningPrimaryChannel(_IntegrationBase):
    """(3) PLAN-179 W1-b exit criterion (b) — pinning comes from CODE.

    The claim is not "a block appears" but "the block cannot have come from the
    compacted transcript". The instrument for that is an EMPTY world: no
    PreCompact ran, so there is no snapshot in either scope and no scratchpad
    entry to assemble anything from. If the pinned set were derived from stored
    state, the payload here would be empty."""

    def test_compact_source_returns_full_set_from_an_empty_world(self):
        # Positive control on "empty": both scopes are genuinely empty first.
        self.assertIsNone(self.read_blob(plan_id=self.PLAN_ID))
        self.assertIsNone(self.read_blob(session_id=self.SESSION_NO_PLAN))

        expected = self.constraint_block()
        out = self.run_pin({"source": "compact", "session_id": self.SESSION_NO_PLAN,
                            "cwd": self.cwd})
        hso = out.get("hookSpecificOutput")
        self.assertIsNotNone(hso, "the PRIMARY pinning channel emitted nothing")
        self.assertEqual(hso["hookEventName"], "SessionStart")
        lines = hso["additionalContext"].split("\n")
        self.assertEqual(
            lines, expected,
            "the emitted block is not byte-identical to render_pinned_block()",
        )
        # EVERY constraint, not merely some: a truncated governance floor is a
        # silent partial failure, which is why the entries are numbered n/N.
        with _bind_pack_lib():
            pinned = _pack_pc.PINNED_CONSTRAINTS
        self.assertEqual(len(lines), len(pinned) + 1, "header + one line per entry")
        for text in pinned:
            self.assertTrue(
                any(text in line for line in lines),
                "a pinned constraint is missing from the emitted block",
            )

    def test_non_compact_source_is_a_no_op(self):
        # The documented enum is [startup, resume, clear, compact, fork]; every
        # value that is not `compact` — including one a future harness adds —
        # must be a no-op, since a non-compact start read Gate-1 normally and
        # would only pay context tax.
        for source in ("startup", "resume", "clear", "fork", "future-value", ""):
            with self.subTest(source=source):
                self.assertEqual(
                    self.run_pin({"source": source, "cwd": self.cwd}), {},
                    "source=%r produced a pinned block" % source,
                )
        # Absent / wrong-typed source likewise.
        self.assertEqual(self.run_pin({"cwd": self.cwd}), {})
        self.assertEqual(self.run_pin({"source": 7, "cwd": self.cwd}), {})

    def test_dedicated_killswitch(self):
        # PLAN-179 §8.8: pinning has its OWN switch. An operator disarming the
        # continuity SNAPSHOT must not silently disarm the governance floor.
        # PLAN-179 finding A: the NESTING reproduces the original sequence
        # exactly — the first assertion runs with only the continuity switch
        # off, the second with BOTH off.
        with mock.patch.dict(os.environ, {"CEO_COMPACTION_CONTINUITY": "0"}):
            self.assertNotEqual(
                self.run_pin({"source": "compact", "cwd": self.cwd}), {},
                "the snapshot kill-switch also disarmed pinning — the two "
                "switches are coupled again (PLAN-179 §8.8)",
            )
            with mock.patch.dict(os.environ, {"CEO_CONSTRAINT_PINNING": "0"}):
                self.assertEqual(
                    self.run_pin({"source": "compact", "cwd": self.cwd}), {}
                )


class TestBudgetSeparation(_IntegrationBase):
    """(4) Amendment r1-C3 — a work-state pointer can never evict a rule.

    Two independent instruments, because they fail differently:

      (a) REAL saturation, no patching. A snapshot that lights up every pointer
          branch yields 7 pointers; the constraint block is 5 lines; the payload
          is therefore 12 lines. The historical cap is 9. If the two lists ever
          shared one budget again, the payload would be truncated to 9 and this
          assertion fires — with no mock in sight.
      (b) PAST-THE-CAP saturation. `_build_pointers` caps itself at 9, so no
          real snapshot can hand `gate()` more than that. Patching it to return
          20 lines targets the SEPARATION in `gate()` rather than re-testing the
          cap, and covers a future pointer set larger than today's."""

    def _saturating_blob(self) -> Dict[str, Any]:
        # ts far in the past so the >12h staleness pointer also fires.
        return {
            "schema": "compaction-continuity/v1",
            "ts": time.time() - (24 * 3600),
            "trigger": "manual",
            "plan_id": self.PLAN_ID,
            "scope_kind": "plan",
            "execution_unit": {"plan_path": ".claude/plans/x.md", "line": 4},
            "ceremony_flags": ["scripts/local/finish-x.sh"],
            "hmac_chain": {"chain_length": 42, "last_hmac_prefix": "abc123def456"},
        }

    def test_real_saturation_is_not_truncated_to_the_pointer_cap(self):
        expected = self.constraint_block()
        self.plant_blob(self._saturating_blob())
        out = self.run_post({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN})
        lines = out["hookSpecificOutput"]["additionalContext"].split("\n")

        self.assertEqual(lines[:len(expected)], expected,
                         "the constraint block is not first, or not intact")
        pointers = lines[len(expected):]
        self.assertGreater(
            len(pointers), 1, "the saturating snapshot produced no real pointers"
        )
        self.assertGreater(
            len(lines), 9,
            "the payload is <=9 lines: the pointer cap swallowed the whole "
            "block, so the budgets are shared again (r1-C3)",
        )
        # And the pointer list alone still honours its own cap.
        self.assertLessEqual(len(pointers), 9)
        # No constraint text may appear among the pointers, and no pointer text
        # among the constraints — a merged list would satisfy the order check
        # above by accident.
        for line in pointers:
            self.assertNotIn("PINNED CONSTRAINT", line)

    def test_pointer_flood_cannot_touch_the_constraint_block(self):
        expected = self.constraint_block()
        flood = ["FAKE POINTER %02d" % n for n in range(20)]
        with mock.patch.object(_post_hook, "_build_pointers", return_value=flood):
            out = self.run_post({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN})
        lines = out["hookSpecificOutput"]["additionalContext"].split("\n")
        self.assertEqual(
            lines, expected + flood,
            "20 pointers changed the constraint block — the budgets are not "
            "separate (r1-C3)",
        )


class TestSnapshotRedaction(_IntegrationBase):
    """(5) Amendment 8.3 (debate C9) — the redaction claim is TRUE on the path.

    The hook has always DOCUMENTED the snapshot as "secrets-redacted by
    state_store.set". That claim was false on the only path the hook took:
    `state_store.set` redacts `isinstance(value, str)` ONLY, and the hook handed
    it `payload.encode("utf-8")` — bytes, which the store trusts verbatim. The
    test plants a secret where the snapshot ingests DISK content (the plan's
    checkbox label) and reads the stored blob back out."""

    SECRET = "sk-ant-api03-AAAAAAAAAAAAAAAAAAAA"

    def test_secret_in_plan_label_is_redacted_in_the_stored_blob(self):
        self.write_plan_file("- [ ] deploy with %s now\n" % self.SECRET)
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                      "trigger": "manual"})
        raw = self.read_blob(plan_id=self.PLAN_ID)
        self.assertIsNotNone(raw, "snapshot was not persisted")
        stored = raw.decode("utf-8") if isinstance(raw, bytes) else raw

        self.assertNotIn(self.SECRET, stored,
                         "the planted token survived into the store")
        self.assertIn(
            "[API_KEY]", stored,
            "no redaction marker in the stored blob — the value went in as "
            "bytes again and state_store's redactor never ran",
        )
        # Positive control on the INGEST: the label really is the field that
        # carries disk content into the blob, so the assertion above is not
        # passing merely because nothing was captured.
        blob = json.loads(stored)
        self.assertIn("label", blob.get("execution_unit", {}),
                      "no label was captured — the redaction test is vacuous")
        self.assertIn("[API_KEY]", blob["execution_unit"]["label"])

    def test_secret_never_reaches_the_reinjected_context(self):
        # The trust boundary the pointers-only doctrine defends: the label is
        # file CONTENT and must not reach the model's instruction stream at
        # all, redacted or not.
        self.write_plan_file("- [ ] deploy with %s now\n" % self.SECRET)
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                      "trigger": "manual"})
        out = self.run_post({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN})
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn(self.SECRET, ctx)
        self.assertNotIn("deploy with", ctx)


class TestReinjectCounters(_IntegrationBase):
    """(6) PLAN-179 W1-b — the two counters mean two different things.

    `pointer_count` keeps its historical meaning (pointers only, 0..9);
    `constraint_count` is the NEW, separate counter for the pinned set. It is
    an integer on purpose: the field is HMAC-covered and canonical_json refuses
    floats, which would discard the WHOLE event rather than the one field
    ([[feedback-float-in-hmac-field-drops-whole-event]])."""

    def test_pointer_count_counts_pointers_only(self):
        expected = self.constraint_block()
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                      "trigger": "manual"})
        out = self.run_post({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN})
        lines = out["hookSpecificOutput"]["additionalContext"].split("\n")
        ev = self.one_event("compaction_context_reinjected")
        self.assertEqual(
            ev["pointer_count"], len(lines) - len(expected),
            "pointer_count does not match the number of POINTER lines — it is "
            "counting constraints too, which would make the 0..9 enum lie",
        )
        # The pointer TEXT never reaches the wire.
        for forbidden in ("additionalContext", "pointers", "label", "plan_path"):
            self.assertNotIn(forbidden, ev)

    def test_reinject_event_carries_integer_constraint_count(self):
        """PLAN-179 W1-b exit — the counter must LAND on the wire.

        The hook sends a real clamped `int`. If this is red, the field is being
        dropped by `_scrub_ceo_boot_event`, i.e. `constraint_count` is missing
        from `_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST` in `_lib/audit_emit.py`
        (and, alongside it, the dispatch-branch int clamp next to
        `pointer_count`, plus the SPEC row). That is an audit-owner ceremony
        item, and until it runs the counter exists only in the producer."""
        self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                      "trigger": "manual"})
        self.run_post({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN})
        ev = self.one_event("compaction_context_reinjected")
        with _bind_pack_lib():
            expected_count = _pack_pc.constraint_count()
        self.assertIn(
            "constraint_count", ev,
            "constraint_count is absent from the emitted event — the "
            "deny-by-default scrub dropped it (allowlist + dispatch clamp + "
            "SPEC row are still owed by the audit-owner ceremony)",
        )
        self.assertIsInstance(ev["constraint_count"], int)
        self.assertNotIsInstance(ev["constraint_count"], bool)
        self.assertEqual(ev["constraint_count"], expected_count)

    def test_constraint_count_is_zero_when_pinning_is_disarmed(self):
        # PLAN-179 finding A: sanctioned form; the switch is still "0" for the
        # whole pipeline run below.
        with mock.patch.dict(os.environ, {"CEO_CONSTRAINT_PINNING": "0"}):
            self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                          "trigger": "manual"})
            out = self.run_post(
                {"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN}
            )
        lines = out["hookSpecificOutput"]["additionalContext"].split("\n")
        for line in lines:
            self.assertNotIn("PINNED CONSTRAINT", line)


class TestContextPressureInstrumentFires(_IntegrationBase):
    """(+) PLAN-179 W0 US2b — the dead instrument is alive.

    The cross-file pass found three defects of one class in `_progress_guard`,
    every one of which made the guard run and emit NOTHING observable:

      1. the edge trigger was probed as `audit_emit.edge_trigger_should_emit`,
         a name that does not exist, so the probe matched None on every run and
         the guard returned before emitting;
      2. the fields were `used_tokens_bucket` / `floor_tokens`, neither of which
         is in the deny-by-default `_CONTEXT_PRESSURE_OBSERVED_ALLOWLIST`, so
         the wire carried a coerced `used_bucket=0` forever;
      3. the bucket was a TOKEN-COUNT rung, which can never satisfy the
         type-strict percent check `used_bucket in {40,60,80,90,95}`.

    A compile-clean guard with any of those still passes every unit test that
    does not look at the wire. So this looks at the wire."""

    def _pressure_event(self, used: int, size: int) -> Dict[str, Any]:
        # Candidate shapes mirror `.claude/scripts/statusline-ceo.py:context_pct()`
        # — the in-repo precedent for this harness payload, not a guess.
        return {
            "cwd": self.cwd,
            "session_id": self.SESSION_WITH_PLAN,
            "trigger": "auto",
            "context_window": {"used_tokens": used, "context_window_size": size},
        }

    # PLAN-179 finding A: the measured floor is armed through `mock.patch.dict`
    # in each test below instead of a direct `os.environ[...] =` write. The
    # value ("1000") and the scope (the whole run_pre call) are unchanged, so
    # `test_guard_is_a_no_op_without_a_measured_floor` stays the real control.
    _FLOOR_ARMED = {"CEO_CONTEXT_PROGRESS_FLOOR_TOKENS": "1000"}

    def test_percent_rung_reaches_the_wire(self):
        with mock.patch.dict(os.environ, self._FLOOR_ARMED):
            self.run_pre(self._pressure_event(82000, 100000))
        ev = self.one_event("context_pressure_observed")
        with _bind_pack_lib():
            rungs = _pack_ae._CONTEXT_PRESSURE_USED_BUCKETS_PCT
        self.assertIn(
            ev["used_bucket"], rungs,
            "used_bucket is not a real percent rung — it was coerced to the "
            "absent sentinel, which is what a token-count bucket always does",
        )
        self.assertEqual(ev["used_bucket"], 80, "82%% should floor onto the 80 rung")
        self.assertIsInstance(ev["used_bucket"], int)
        self.assertNotIsInstance(ev["used_bucket"], bool)
        self.assertEqual(ev["event_source"], "precompact")
        self.assertEqual(ev["plan_id"], self.PLAN_ID)
        # Raw counts are a transcript-size side channel and are NOT allowlisted.
        for forbidden in ("used_tokens", "floor_tokens", "used_tokens_bucket"):
            self.assertNotIn(forbidden, ev)

    def test_edge_triggered_not_per_call(self):
        # Hysteresis (OQ-4): a session sitting in one rung must not flood the
        # HMAC chain with one row per compaction.
        with mock.patch.dict(os.environ, self._FLOOR_ARMED):
            self.run_pre(self._pressure_event(82000, 100000))
            self.run_pre(self._pressure_event(83000, 100000))  # same 80 rung
            self.assertEqual(len(self.events("context_pressure_observed")), 1)
            self.run_pre(self._pressure_event(96000, 100000))  # crosses to 95
        buckets = [e["used_bucket"] for e in self.events("context_pressure_observed")]
        self.assertEqual(buckets, [80, 95], "the rung TRANSITION did not emit")

    def test_guard_is_a_no_op_without_a_measured_floor(self):
        # PLAN-179 is explicit that a floor invented ahead of the W0 measurement
        # would be worse than none, so an unset env var means silence — not a
        # default. This is the control that keeps the two tests above honest:
        # if the guard emitted unconditionally, they would prove nothing.
        self.run_pre(self._pressure_event(82000, 100000))
        self.assertEqual(self.events("context_pressure_observed"), [])

    def test_no_percent_in_the_payload_emits_the_documented_sentinel(self):
        # Residual named by the pack: PreCompact is not DOCUMENTED to carry
        # context-window accounting. When it does not, the hook must emit
        # audit_emit's 0 sentinel rather than invent a denominator.
        with mock.patch.dict(os.environ, self._FLOOR_ARMED):
            self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                          "trigger": "auto", "used_tokens": 82000})
        ev = self.one_event("context_pressure_observed")
        self.assertEqual(ev["used_bucket"], 0)
        self.assertEqual(ev["event_source"], "precompact")


class TestKillSwitchAndFailOpen(_IntegrationBase):
    """The pipeline must never wedge a session — ADVISORY, fail-open."""

    def test_continuity_killswitch_silences_both_halves(self):
        # PLAN-179 finding A: sanctioned form; the switch stays "0" across BOTH
        # halves of the pipeline, which is the whole claim of this test.
        with mock.patch.dict(os.environ, {"CEO_COMPACTION_CONTINUITY": "0"}):
            self.assertEqual(
                self.run_pre({"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN,
                              "trigger": "manual"}), {})
            self.assertEqual(
                self.run_post(
                    {"cwd": self.cwd, "session_id": self.SESSION_WITH_PLAN}
                ), {})
        self.assertEqual(self.events("compaction_continuity_snapshot"), [])
        self.assertEqual(self.events("compaction_context_reinjected"), [])

    def test_empty_event_never_raises(self):
        # A harness that changes its payload shape must degrade, not crash.
        with _bind_pack_lib():
            self.assertEqual(_pre_hook.gate({}, self.cwd), {})
            _post_hook.gate({})
            self.assertEqual(_pin_hook.gate({}), {})


if __name__ == "__main__":
    unittest.main()
