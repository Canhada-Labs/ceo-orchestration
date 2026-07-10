"""Tests for PLAN-154 item 5 — `_lib/advisory_dampen.py` (A10 contract).

COUPLING NOTE: STAGED test (PLAN-154 SENT-F staging discipline — same
dual-context pattern as tests/test_bash_citation_gate.py). The module under
test is loaded CANONICAL-FIRST (`.claude/hooks/_lib/advisory_dampen.py`,
post-ceremony tree), falling back to the staged SOURCE copy at
`.claude/plans/PLAN-154/staged/sent-f/` (pre-ceremony live tree).

Contract under test (PLAN-154 constraint 4 / consensus A10):

  * Dampening keys on the schema DECISION field, never a text heuristic:
    decision="deny"/"block"/anything-unknown => text returned VERBATIM
    (byte-identical), uncounted, zero state I/O.
  * CI POSITIVE CONTROL: a block reason is byte-identical at N=1 vs N=100.
  * A condensed advisory ALWAYS retains {advisory ID, ordinal count,
    pointer-to-full-text}.
  * Counters are session-scoped in a per-session 0600 state file
    (tool_lifecycle pattern), off the audit hot path.
  * <= 1 condensation audit event (`advisory_dampened`) per advisory ID
    per session.
  * Kill switches: CEO_ADVISORY_DAMPEN=0 / CEO_SOTA_DISABLE=1 => full text.
  * Injectable now_fn (A9); wall clock only as default.
  * INFRASTRUCTURE failure => full text (legibility never lost).

INERT TEST DATA: every advisory string below is fixture DATA fed to a pure
formatting/counting library — nothing is executed or rendered to a model.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

# --- Locate repo root + pick the module source (canonical-first, staged
# fallback — see module docstring). ---
_THIS = Path(__file__).resolve()
_repo_root = None
for _parent in _THIS.parents:
    if (_parent / ".claude" / "hooks" / "_lib" / "__init__.py").is_file() and (
        _parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = _parent
        break
assert _repo_root is not None, "could not locate repo root from test path"
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_CANONICAL_MOD = _LIVE_HOOKS / "_lib" / "advisory_dampen.py"
_STAGED_MOD = (
    _repo_root
    / ".claude" / "plans" / "PLAN-154" / "staged" / "sent-f"
    / ".claude" / "hooks" / "_lib" / "advisory_dampen.py"
)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_emit  # noqa: E402
from _lib import trusted_env  # noqa: E402


def _load_advisory_dampen():
    """Load advisory_dampen canonical-first / staged-fallback under a
    private module name (never mutates the `_lib` package namespace)."""
    src = _CANONICAL_MOD if _CANONICAL_MOD.is_file() else _STAGED_MOD
    assert src.is_file(), "advisory_dampen.py not found (canonical or staged)"
    spec = importlib.util.spec_from_file_location(
        "staged_advisory_dampen", str(src)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["staged_advisory_dampen"] = mod
    spec.loader.exec_module(mod)
    return mod


ad = _load_advisory_dampen()

# INERT fixture prose.
_ADVISORY_TEXT = (
    "[check_bash_safety] FACT-GATE shadow advisory: this destructive "
    "command [sha256 0123456789abcdef] would be denied under ENFORCE."
)
_BLOCK_TEXT = (
    "BLOCKED: `rm` with -r and -f is destructive. Specify exact files."
)


class _DampenBase(TestEnvContext):
    """Isolated env + a fixed session id for state-path determinism."""

    SESSION_ID = "s-dampen-1"

    def setUp(self):
        super().setUp()
        self._sid_patch = mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": self.SESSION_ID}
        )
        self._sid_patch.start()
        # Neutralize any dev-shell kill switches captured in the import-time
        # trusted snapshot ("" is inert for both polarities); tests that
        # exercise the switches patch real values on top of this.
        self._env_neutral = mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {"CEO_ADVISORY_DAMPEN": "", "CEO_SOTA_DISABLE": ""},
        )
        self._env_neutral.start()

    def tearDown(self):
        self._env_neutral.stop()
        self._sid_patch.stop()
        super().tearDown()

    # -- helpers ----------------------------------------------------------

    def _dampen(self, text=_ADVISORY_TEXT, decision="advisory", **kw):
        kw.setdefault("session_id", self.SESSION_ID)
        return ad.dampen("adv.test.id", text, decision=decision, **kw)

    def _state_dir(self) -> Path:
        # TestEnvContext points CEO_AUDIT_LOG_DIR at self.audit_dir, which
        # the module resolves as its state base dir.
        return self.audit_dir / "advisory-dampen"

    def _state_file(self) -> Path:
        return self._state_dir() / (self.SESSION_ID + ".json")


# ---------------------------------------------------------------------------
# A10 point 1 — decision-field keying (never a text heuristic).
# ---------------------------------------------------------------------------
class TestDecisionFieldKeying(_DampenBase):
    def test_block_decision_exempt_and_verbatim(self):
        res = self._dampen(text=_BLOCK_TEXT, decision="block")
        self.assertTrue(res.exempt)
        self.assertFalse(res.condensed)
        self.assertEqual(res.text, _BLOCK_TEXT)

    def test_deny_decision_exempt_and_verbatim(self):
        res = self._dampen(text=_BLOCK_TEXT, decision="deny")
        self.assertTrue(res.exempt)
        self.assertEqual(res.text, _BLOCK_TEXT)

    def test_unknown_decision_is_exempt_fail_closed_toward_legibility(self):
        res = self._dampen(decision="warning")  # not in the closed enum
        self.assertTrue(res.exempt)
        self.assertEqual(res.text, _ADVISORY_TEXT)

    def test_exempt_path_performs_zero_state_io(self):
        for _ in range(5):
            self._dampen(text=_BLOCK_TEXT, decision="block")
        self.assertFalse(self._state_dir().exists())

    def test_advisory_looking_block_text_is_still_exempt(self):
        # The classifier is the DECISION FIELD, not the prose: a block whose
        # text says "advisory" everywhere is still exempt.
        tricky = "advisory advisory advisory (but decision=block)"
        for _ in range(3):
            res = self._dampen(text=tricky, decision="block")
            self.assertEqual(res.text, tricky)
            self.assertTrue(res.exempt)

    def test_block_reason_byte_identical_n1_vs_n100(self):
        """CI POSITIVE CONTROL (A10): block reason byte-identical at N=1 vs
        N=100 — dampening can never erode a blocking guard's legibility."""
        outputs = set()
        for _ in range(100):
            outputs.add(self._dampen(text=_BLOCK_TEXT, decision="block").text)
        self.assertEqual(outputs, {_BLOCK_TEXT})


# ---------------------------------------------------------------------------
# Condensation behavior.
# ---------------------------------------------------------------------------
class TestCondensation(_DampenBase):
    def test_first_occurrence_full_text_ordinal_1(self):
        res = self._dampen()
        self.assertEqual(res.text, _ADVISORY_TEXT)
        self.assertEqual(res.ordinal, 1)
        self.assertFalse(res.condensed)
        self.assertFalse(res.exempt)

    def test_repeat_condensed_retains_id_ordinal_pointer(self):
        self._dampen()
        res = self._dampen()
        self.assertTrue(res.condensed)
        self.assertEqual(res.ordinal, 2)
        self.assertNotEqual(res.text, _ADVISORY_TEXT)
        # A10 point 3 — the condensed form ALWAYS retains:
        self.assertIn("adv.test.id", res.text)          # advisory ID
        self.assertIn("x2", res.text)                   # ordinal count
        self.assertIn("first occurrence", res.text)     # pointer-to-full-text
        self.assertIn("CEO_ADVISORY_DAMPEN=0", res.text)  # un-dampen pointer

    def test_ordinal_monotonic_across_repeats(self):
        ordinals = [self._dampen().ordinal for _ in range(4)]
        self.assertEqual(ordinals, [1, 2, 3, 4])

    def test_distinct_ids_do_not_share_counters(self):
        first = ad.dampen(
            "adv.id.a", _ADVISORY_TEXT, decision="advisory",
            session_id=self.SESSION_ID,
        )
        other = ad.dampen(
            "adv.id.b", _ADVISORY_TEXT, decision="advisory",
            session_id=self.SESSION_ID,
        )
        self.assertEqual((first.ordinal, other.ordinal), (1, 1))
        self.assertFalse(other.condensed)

    def test_advisory_id_is_sanitized_no_traversal(self):
        res = ad.dampen(
            "../../etc/passwd", _ADVISORY_TEXT, decision="advisory",
            session_id=self.SESSION_ID,
        )
        self.assertEqual(res.ordinal, 1)
        # State stays inside the advisory-dampen subdir (no traversal).
        files = list(self._state_dir().glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].parent, self._state_dir())

    def test_untracked_beyond_id_bound_returns_full_text(self):
        # Pre-fill the state file with _MAX_TRACKED_IDS counters; a NEW id
        # must come back full-text ordinal 1 (bounded map, never condensed).
        import json as _json
        self._state_dir().mkdir(parents=True, exist_ok=True)
        counters = {
            "id%03d" % i: {"count": 3, "emitted": True, "first_s": 1.0}
            for i in range(ad._MAX_TRACKED_IDS)
        }
        self._state_file().write_text(
            _json.dumps({"counters": counters}), encoding="utf-8"
        )
        res = self._dampen()
        self.assertEqual((res.ordinal, res.condensed), (1, False))
        self.assertEqual(res.text, _ADVISORY_TEXT)


# ---------------------------------------------------------------------------
# Session-scoped 0600 state (tool_lifecycle pattern).
# ---------------------------------------------------------------------------
class TestSessionScopedState(_DampenBase):
    def test_state_file_created_0600_under_advisory_dampen_subdir(self):
        self._dampen()
        f = self._state_file()
        self.assertTrue(f.is_file())
        mode = stat.S_IMODE(f.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_counters_are_session_scoped(self):
        self._dampen()
        self._dampen()  # ordinal 2 in session A
        res_other = ad.dampen(
            "adv.test.id", _ADVISORY_TEXT, decision="advisory",
            session_id="s-dampen-OTHER",
        )
        self.assertEqual(res_other.ordinal, 1)  # fresh scope
        self.assertFalse(res_other.condensed)
        self.assertTrue(
            (self._state_dir() / "s-dampen-OTHER.json").is_file()
        )

    def test_session_id_component_is_traversal_safe(self):
        ad.dampen(
            "adv.test.id", _ADVISORY_TEXT, decision="advisory",
            session_id="../../evil",
        )
        # Everything stays inside the subdir.
        for f in self._state_dir().glob("*"):
            self.assertEqual(f.parent, self._state_dir())
        self.assertFalse((self.audit_dir.parent / "evil.json").exists())

    def test_now_fn_injectable_stamps_first_seen(self):
        import json as _json
        self._dampen(now_fn=lambda: 12345.5)
        data = _json.loads(self._state_file().read_text(encoding="utf-8"))
        rec = data["counters"]["adv.test.id"]
        self.assertEqual(rec["first_s"], 12345.5)


# ---------------------------------------------------------------------------
# Audit event: <=1 condensation event per advisory ID per session.
# ---------------------------------------------------------------------------
class TestCondensationAuditEvent(_DampenBase):
    def test_at_most_one_event_per_id_per_session(self):
        with mock.patch.object(audit_emit, "emit_generic") as emit:
            for _ in range(6):
                self._dampen()
        dampened = [
            c for c in emit.call_args_list
            if c.args and c.args[0] == "advisory_dampened"
        ]
        self.assertEqual(len(dampened), 1)
        kwargs = dampened[0].kwargs
        self.assertEqual(kwargs.get("advisory_id"), "adv.test.id")
        self.assertEqual(kwargs.get("ordinal"), 2)  # first condensation
        self.assertEqual(kwargs.get("channel"), "stderr_prose")
        self.assertEqual(kwargs.get("session_id"), self.SESSION_ID)

    def test_event_carries_metadata_only_never_the_text(self):
        with mock.patch.object(audit_emit, "emit_generic") as emit:
            self._dampen()
            self._dampen()
        dampened = [
            c for c in emit.call_args_list
            if c.args and c.args[0] == "advisory_dampened"
        ]
        self.assertEqual(len(dampened), 1)
        for value in dampened[0].kwargs.values():
            if isinstance(value, str):
                self.assertNotIn("FACT-GATE shadow advisory", value)

    def test_emit_failure_is_fail_open_full_behavior(self):
        with mock.patch.object(
            audit_emit, "emit_generic", side_effect=RuntimeError("boom")
        ):
            self._dampen()
            res = self._dampen()  # emit raises inside; must not propagate
        self.assertTrue(res.condensed)
        self.assertEqual(res.ordinal, 2)


# ---------------------------------------------------------------------------
# Kill switches (A12) — read from the trusted_env snapshot.
# ---------------------------------------------------------------------------
class TestKillSwitches(_DampenBase):
    def test_ceo_advisory_dampen_0_disables_condensation(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_ADVISORY_DAMPEN": "0"}
        ):
            for _ in range(3):
                res = self._dampen()
                self.assertEqual(res.text, _ADVISORY_TEXT)
                self.assertFalse(res.condensed)

    def test_sota_master_kill_disables_condensation(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_SOTA_DISABLE": "1"}
        ):
            for _ in range(3):
                res = self._dampen()
                self.assertEqual(res.text, _ADVISORY_TEXT)
                self.assertFalse(res.condensed)

    def test_default_unset_is_enabled(self):
        with mock.patch.dict(trusted_env.ORIGINAL_CEO_ENV, {}, clear=True):
            self._dampen()
            self.assertTrue(self._dampen().condensed)


# ---------------------------------------------------------------------------
# Infrastructure fail-open toward FULL text.
# ---------------------------------------------------------------------------
class TestInfrastructureFailOpen(_DampenBase):
    def test_state_load_failure_returns_full_text(self):
        with mock.patch.object(
            ad, "_load_state", side_effect=OSError("simulated I/O error")
        ):
            res = self._dampen()
        self.assertEqual(res.text, _ADVISORY_TEXT)
        self.assertEqual((res.ordinal, res.condensed, res.exempt),
                         (1, False, False))

    def test_state_save_failure_never_loses_text(self):
        # _save_state is itself fail-open; even a raising variant must not
        # cost the caller the text.
        with mock.patch.object(
            ad, "_save_state", side_effect=OSError("disk full")
        ):
            res = self._dampen()
        self.assertEqual(res.text, _ADVISORY_TEXT)

    def test_clock_failure_returns_full_text(self):
        def _broken_clock():
            raise RuntimeError("no clock")

        res = self._dampen(now_fn=_broken_clock)
        self.assertEqual(res.text, _ADVISORY_TEXT)
        self.assertFalse(res.condensed)


if __name__ == "__main__":
    unittest.main()
