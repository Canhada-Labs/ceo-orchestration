"""Tests for PLAN-154 item 6 — the fact-forcing DENY-ONCE gate
(ADVISORY->ENFORCE path) in check_bash_safety.py.

COUPLING NOTE: STAGED test (PLAN-154 SENT-F staging discipline — same
dual-context pattern as tests/test_bash_citation_gate.py). Loads the
fact-gate check_bash_safety.py CANONICAL-FIRST (post-ceremony tree),
falling back to the staged SOURCE copy at
`.claude/plans/PLAN-154/staged/sent-f/` (pre-ceremony live tree). The
`_lib` package is always the canonical one; `_lib.advisory_dampen` (a NEW
module staged in the same SENT-F batch) is import-shimmed from the staged
tree when the canonical copy does not exist yet.

Contract under test (PLAN-154 item 6 / consensus A8; ADR-160):

  * SHADOW (default): decision byte-identical to legacy (including the
    ADR-175 pilot when armed); the gate only records deny-once state,
    emits shadow telemetry (`veto_triggered` +
    reason_code=fact_gate_shadow_deny|fact_gate_shadow_release), and
    prints ONE dampened stderr advisory (the wired item-5 consumer).
  * ENFORCE (settings-backed `env.CEO_FACT_GATE_ENFORCE == "1"` — the env
    var can NEVER enable; it is emergency-off only): destructive Bash is
    denied once per session per `sha256(normalized command)`; a retry
    releases ONLY on an exact-hash match + a verified citation. First
    attempts never release, even citation-bearing. The ADR-175 pilot gate
    is skipped while enforce is active (its first-attempt allow path must
    not undercut deny-once).
  * REQUIRED fixtures: transcript-read-failure => BLOCK;
    fabricated-citation => BLOCK (fail-CLOSED, C4/_e3).
  * The deny message states the EXACT citation format that unlocks retry
    and is byte-identical at N=1 vs N=100 (A10 positive control).
  * Every observed activation change emits `fact_gate_activation_changed`;
    env emergency-off emits ONE `learning_rail_disabled` breadcrumb per
    session (A12).
  * Kill precedence: CEO_SOTA_DISABLE=1 > CEO_FACT_GATE_SHADOW=0 /
    CEO_FACT_GATE_ENFORCE=0 > defaults. Structurally off => zero
    filesystem delta.

INERT TEST DATA (Wave E doctrine 5): every command string and transcript
line in this file is fixture DATA replayed against the gate's decision
functions — nothing here is executed as a shell command.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

# --- Locate repo root + pick the fact-gate hook source (canonical-first,
# staged fallback — see module docstring). ---
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
_CANONICAL_CBS = _LIVE_HOOKS / "check_bash_safety.py"
_STAGED_ROOT = (
    _repo_root / ".claude" / "plans" / "PLAN-154" / "staged" / "sent-f"
)
_STAGED_CBS = _STAGED_ROOT / ".claude" / "hooks" / "check_bash_safety.py"
_STAGED_ADV = (
    _STAGED_ROOT / ".claude" / "hooks" / "_lib" / "advisory_dampen.py"
)
# The fact-gate marker distinguishing a post-apply canonical copy from a
# pre-apply live one.
_FACT_MARKER = "def _apply_fact_gate"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "fact-gate source not found in canonical (%s) or staged (%s); "
        "marker=%r" % (canonical, staged, marker)
    )


if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import trusted_env  # noqa: E402
from _lib import effective_config  # noqa: E402


def _ensure_advisory_dampen_importable() -> None:
    """Pre-ceremony shim: `_lib.advisory_dampen` ships in the same SENT-F
    batch as the fact gate; until it lands, register the staged copy so the
    gate's lazy `from _lib import advisory_dampen` resolves. Post-ceremony
    the canonical import wins and this is a no-op."""
    try:
        import _lib.advisory_dampen  # noqa: F401
        return
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "_lib.advisory_dampen", str(_STAGED_ADV)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_lib.advisory_dampen"] = mod
    spec.loader.exec_module(mod)
    import _lib
    setattr(_lib, "advisory_dampen", mod)


_ensure_advisory_dampen_importable()


def _load_cbs():
    """Load the fact-gate check_bash_safety module under a private name
    (test_bash_citation_gate.py `_load_cbs` pattern — the staged dir is
    removed from sys.path after exec)."""
    src = _pick(_CANONICAL_CBS, _STAGED_CBS, _FACT_MARKER)
    spec = importlib.util.spec_from_file_location(
        "staged_check_bash_safety_fact_gate", str(src)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["staged_check_bash_safety_fact_gate"] = mod
    staged_dir = str(src.parent)
    was_absent = staged_dir not in sys.path
    try:
        spec.loader.exec_module(mod)
    finally:
        if (
            was_absent
            and staged_dir != str(_LIVE_HOOKS)
            and staged_dir in sys.path
        ):
            sys.path.remove(staged_dir)
    return mod


cbs = _load_cbs()

# ---------------------------------------------------------------------------
# INERT TEST DATA — fixture strings only, never executed.
# ---------------------------------------------------------------------------
_CITED = "please remove the scratch directory at /tmp/scratch-fg entirely"
_CMD_PLAIN = "rm -rf /tmp/scratch-fg"
_CMD_CITED = "CEO_DESTRUCTIVE_CITE='transcript:%s' %s" % (_CITED, _CMD_PLAIN)
_SESSION = "s-fact-gate-1"


class _FactGateBase(TestEnvContext):
    """Isolated env + neutralized trusted snapshot + hermetic settings."""

    def setUp(self):
        super().setUp()
        self._sid_patch = mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": _SESSION}
        )
        self._sid_patch.start()
        # Neutralize dev-shell values captured in the import-time trusted
        # snapshot ("" is inert for every polarity below); tests patch real
        # values on top. mock.patch.dict — never a direct os.environ write.
        self._env_neutral = mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {
                "CEO_SOTA_DISABLE": "",
                "CEO_FACT_GATE_SHADOW": "",
                "CEO_FACT_GATE_ENFORCE": "",
                "CEO_DESTRUCTIVE_CITATION_GATE": "",
                "CEO_ADVISORY_DAMPEN": "",
            },
        )
        self._env_neutral.start()
        # Hermetic settings layers: no managed policy file from the host.
        self._managed_patch = mock.patch.object(
            effective_config, "_managed_settings_paths", return_value=[]
        )
        self._managed_patch.start()

    def tearDown(self):
        self._managed_patch.stop()
        self._env_neutral.stop()
        self._sid_patch.stop()
        super().tearDown()

    # -- helpers ----------------------------------------------------------

    def _write_transcript(self, text: str, name: str = "session.jsonl") -> Path:
        tdir = self.home_dir / ".claude" / "projects" / "test-fg"
        tdir.mkdir(parents=True, exist_ok=True)
        tp = tdir / name
        line = json.dumps(
            {"type": "user", "message": {"role": "user", "content": text}}
        )
        tp.write_text(line + "\n", encoding="utf-8")
        return tp

    def _set_enforce_settings(self, value: str = "1") -> None:
        """The settings-backed flip artifact (A8): env.CEO_FACT_GATE_ENFORCE
        in the project's settings.local.json layer."""
        target = self.project_dir / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"env": {"CEO_FACT_GATE_ENFORCE": value}}),
            encoding="utf-8",
        )

    def _clear_enforce_settings(self) -> None:
        target = self.project_dir / ".claude" / "settings.local.json"
        if target.is_file():
            target.unlink()

    def _run_main(self, command: str, transcript_path: str = "") -> "tuple":
        """Drive cbs.main() end-to-end. Returns (decision_dict, stderr_text)."""
        payload = {
            "session_id": _SESSION,
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }
        if transcript_path:
            payload["transcript_path"] = transcript_path
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(sys, "stdin", stdin), mock.patch.object(
            sys, "stdout", stdout
        ), mock.patch.object(sys, "stderr", stderr):
            rc = cbs.main()
        self.assertEqual(rc, 0)
        out = stdout.getvalue().strip()
        self.assertTrue(out, "hook must emit exactly one JSON line")
        return json.loads(out.splitlines()[-1]), stderr.getvalue()

    def _audit_events(self, reason_code=None):
        log = self.audit_dir / "audit-log.jsonl"
        if not log.exists():
            return []
        events = []
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if reason_code is None or ev.get("reason_code") == reason_code:
                events.append(ev)
        return events

    def _state_file(self) -> Path:
        return self.audit_dir / "fact-gate" / (_SESSION + ".json")

    def _expected_sha(self, command: str) -> str:
        normalized = cbs._fact_gate_normalize(command)
        assert normalized is not None
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Normalization (pure) — the exact-hash release contract substrate.
# ---------------------------------------------------------------------------
class TestNormalization(TestEnvContext):
    def test_strips_only_the_cite_assignment(self):
        self.assertEqual(
            cbs._fact_gate_normalize(_CMD_CITED),
            cbs._fact_gate_normalize(_CMD_PLAIN),
        )

    def test_other_env_prefixes_change_the_hash(self):
        self.assertNotEqual(
            cbs._fact_gate_normalize("FOO=1 " + _CMD_PLAIN),
            cbs._fact_gate_normalize(_CMD_PLAIN),
        )

    def test_whitespace_and_quoting_are_canonicalized(self):
        self.assertEqual(
            cbs._fact_gate_normalize('rm  -rf   "/tmp/scratch-fg"'),
            cbs._fact_gate_normalize(_CMD_PLAIN),
        )

    def test_unparseable_returns_none(self):
        self.assertIsNone(cbs._fact_gate_normalize('rm -rf /tmp/x "unclosed'))
        self.assertIsNone(cbs._fact_gate_normalize(""))
        self.assertIsNone(cbs._fact_gate_normalize("   "))

    def test_different_target_different_hash(self):
        self.assertNotEqual(
            cbs._fact_gate_normalize("rm -rf /tmp/fg-a"),
            cbs._fact_gate_normalize("rm -rf /tmp/fg-b"),
        )


# ---------------------------------------------------------------------------
# Flip plumbing — settings-backed enable, env emergency-off only.
# ---------------------------------------------------------------------------
class TestEnforceStateResolution(_FactGateBase):
    def test_default_is_advisory(self):
        self.assertEqual(
            cbs._fact_gate_enforce_state(), (False, "default_advisory")
        )

    def test_settings_layer_enables(self):
        self._set_enforce_settings("1")
        self.assertEqual(cbs._fact_gate_enforce_state(), (True, "settings"))

    def test_settings_non_1_stays_advisory(self):
        self._set_enforce_settings("true")
        self.assertEqual(
            cbs._fact_gate_enforce_state(), (False, "default_advisory")
        )

    def test_env_var_alone_can_never_enable(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_FACT_GATE_ENFORCE": "1"}
        ):
            self.assertEqual(
                cbs._fact_gate_enforce_state(), (False, "default_advisory")
            )

    def test_env_emergency_off_overrides_settings(self):
        self._set_enforce_settings("1")
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_FACT_GATE_ENFORCE": "0"}
        ):
            self.assertEqual(
                cbs._fact_gate_enforce_state(), (False, "env_emergency_off")
            )

    def test_sota_master_kill_wins_over_settings(self):
        self._set_enforce_settings("1")
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_SOTA_DISABLE": "1"}
        ):
            self.assertEqual(
                cbs._fact_gate_enforce_state(), (False, "sota_master_off")
            )

    def test_settings_read_infrastructure_failure_stays_advisory(self):
        self._set_enforce_settings("1")
        with mock.patch.object(
            effective_config, "_layer_paths",
            side_effect=RuntimeError("simulated resolver crash"),
        ):
            self.assertEqual(
                cbs._fact_gate_enforce_state(), (False, "default_advisory")
            )


# ---------------------------------------------------------------------------
# SHADOW mode (the default) — decision untouched, telemetry + state only.
# ---------------------------------------------------------------------------
class TestShadowMode(_FactGateBase):
    def test_decision_byte_identical_to_legacy_block(self):
        legacy = cbs.decide_command(_CMD_PLAIN)
        out, _err = self._run_main(_CMD_PLAIN)
        self.assertEqual(out.get("decision"), "block")
        self.assertEqual(out.get("reason"), legacy.reason)
        self.assertNotIn("FACT GATE", out.get("reason", ""))

    def test_shadow_deny_telemetry_and_0600_state(self):
        self._run_main(_CMD_PLAIN)
        events = self._audit_events("fact_gate_shadow_deny")
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.get("action"), "veto_triggered")
        self.assertEqual(ev.get("gate_outcome"), "shadow_would_deny")
        self.assertEqual(ev.get("fact_gate_mode"), "shadow")
        self.assertEqual(ev.get("cite_status"), "absent")
        self.assertEqual(ev.get("prior_deny"), False)
        self.assertEqual(
            ev.get("command_sha256"), self._expected_sha(_CMD_PLAIN)
        )
        f = self._state_file()
        self.assertTrue(f.is_file())
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)

    def test_shadow_release_event_on_exact_cited_retry(self):
        tp = self._write_transcript(_CITED)
        self._run_main(_CMD_PLAIN, transcript_path=str(tp))       # would-deny
        out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")            # still shadow
        releases = self._audit_events("fact_gate_shadow_release")
        self.assertEqual(len(releases), 1)
        ev = releases[0]
        self.assertEqual(ev.get("gate_outcome"), "shadow_would_release")
        self.assertEqual(ev.get("cite_status"), "verified")
        self.assertEqual(ev.get("prior_deny"), True)
        self.assertEqual(
            ev.get("command_sha256"), self._expected_sha(_CMD_PLAIN)
        )

    def test_shadow_fabricated_citation_retry_records_verify_failed(self):
        tp = self._write_transcript("a completely different instruction line")
        self._run_main(_CMD_PLAIN, transcript_path=str(tp))
        out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        denies = self._audit_events("fact_gate_shadow_deny")
        self.assertEqual(len(denies), 2)
        self.assertEqual(denies[-1].get("cite_status"), "verify_failed")
        self.assertEqual(self._audit_events("fact_gate_shadow_release"), [])

    def test_shadow_keeps_pilot_citation_gate_behavior(self):
        # ADR-175 pilot armed + shadow default: first-attempt valid citation
        # still allows — shadow never changes the decision (A8).
        tp = self._write_transcript(_CITED)
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {"CEO_DESTRUCTIVE_CITATION_GATE": "1"},
        ):
            out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out, {})  # pilot allow, exactly as pre-PLAN-154
        self.assertTrue(self._audit_events("destructive_citation_accepted"))

    def test_shadow_off_switch_zero_filesystem_delta(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_FACT_GATE_SHADOW": "0"}
        ):
            out, err = self._run_main(_CMD_PLAIN)
        self.assertEqual(out.get("decision"), "block")
        self.assertFalse((self.audit_dir / "fact-gate").exists())
        self.assertEqual(self._audit_events("fact_gate_shadow_deny"), [])
        self.assertNotIn("FACT-GATE", err)

    def test_sota_master_kill_zero_filesystem_delta(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_SOTA_DISABLE": "1"}
        ):
            out, err = self._run_main(_CMD_PLAIN)
        self.assertEqual(out.get("decision"), "block")
        self.assertFalse((self.audit_dir / "fact-gate").exists())
        self.assertNotIn("FACT-GATE", err)


# ---------------------------------------------------------------------------
# Item 5 wiring — the shadow stderr advisory is DAMPENED on repeats.
# ---------------------------------------------------------------------------
class TestShadowAdvisoryDampening(_FactGateBase):
    def test_first_full_then_condensed_with_id_and_ordinal(self):
        _out, err1 = self._run_main(_CMD_PLAIN)
        self.assertIn("FACT-GATE shadow advisory", err1)
        self.assertIn("ADR-160", err1)
        _out, err2 = self._run_main(_CMD_PLAIN)
        self.assertIn("[advisory fact_gate_shadow", err2)   # advisory ID
        self.assertIn("x2", err2)                           # ordinal
        self.assertIn("condensed", err2)                    # pointer form
        self.assertNotIn("ADR-160", err2)                   # full prose gone

    def test_block_reason_is_never_dampened_in_shadow(self):
        outs = set()
        for _ in range(3):
            out, _err = self._run_main(_CMD_PLAIN)
            outs.add(out.get("reason"))
        self.assertEqual(len(outs), 1)  # byte-identical across repeats

    def test_dampen_module_failure_falls_open_to_full_text(self):
        import _lib.advisory_dampen as adv
        with mock.patch.object(
            adv, "dampen", side_effect=RuntimeError("boom")
        ):
            _out, err = self._run_main(_CMD_PLAIN)
        self.assertIn("FACT-GATE shadow advisory", err)  # full text retained


# ---------------------------------------------------------------------------
# ENFORCE mode — deny-once + exact-hash cited release.
# ---------------------------------------------------------------------------
class TestEnforceMode(_FactGateBase):
    def setUp(self):
        super().setUp()
        self._set_enforce_settings("1")

    def test_first_attempt_denied_with_exact_citation_format(self):
        out, _err = self._run_main(_CMD_PLAIN)
        self.assertEqual(out.get("decision"), "block")
        reason = out.get("reason", "")
        self.assertIn("BLOCKED", reason)              # legacy reason retained
        self.assertIn("FACT GATE", reason)
        # (d) the EXACT citation format that unlocks retry:
        self.assertIn("CEO_DESTRUCTIVE_CITE='transcript:", reason)
        self.assertIn("VERBATIM", reason)
        denied = self._audit_events("fact_gate_denied")
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0].get("gate_outcome"), "blocked_deny_once")
        self.assertEqual(denied[0].get("fact_gate_mode"), "enforce")

    def test_first_attempt_with_valid_citation_still_denied(self):
        # Release is defined ONLY for retries of a previously-denied exact
        # hash — a citation-bearing first attempt never releases.
        tp = self._write_transcript(_CITED)
        out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("FACT GATE", out.get("reason", ""))
        self.assertEqual(self._audit_events("fact_gate_released"), [])

    def test_deny_then_exact_cited_retry_releases(self):
        tp = self._write_transcript(_CITED)
        first, _err = self._run_main(_CMD_PLAIN, transcript_path=str(tp))
        self.assertEqual(first.get("decision"), "block")
        out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out, {})  # released (allow shape)
        released = self._audit_events("fact_gate_released")
        self.assertEqual(len(released), 1)
        ev = released[0]
        self.assertEqual(
            ev.get("gate_outcome"), "allowed_with_fact_gate_release"
        )
        self.assertEqual(ev.get("cite_status"), "verified")
        self.assertEqual(ev.get("prior_deny"), True)
        self.assertEqual(
            ev.get("command_sha256"), self._expected_sha(_CMD_PLAIN)
        )
        self.assertEqual(ev.get("cite_source_class"), "transcript")
        # Inert-evidence field, redact_secrets route (ADR-175 style).
        self.assertIn(_CITED, ev.get("cited_instruction_data", ""))

    def test_release_requires_exact_hash_match(self):
        tp = self._write_transcript(_CITED)
        self._run_main("rm -rf /tmp/fg-a", transcript_path=str(tp))
        cmd_b = (
            "CEO_DESTRUCTIVE_CITE='transcript:%s' rm -rf /tmp/fg-b" % _CITED
        )
        out, _err = self._run_main(cmd_b, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")  # fresh deny-once
        self.assertEqual(self._audit_events("fact_gate_released"), [])

    def test_retry_without_citation_stays_denied(self):
        self._run_main(_CMD_PLAIN)
        out, _err = self._run_main(_CMD_PLAIN)
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("FACT GATE", out.get("reason", ""))

    def test_transcript_read_failure_blocks(self):
        """REQUIRED fixture (item 6b): release-side verification is
        fail-CLOSED — an unreadable transcript BLOCKS the cited retry."""
        tp = self._write_transcript(_CITED)
        self._run_main(_CMD_PLAIN, transcript_path=str(tp))  # deny once
        with mock.patch.object(
            cbs, "_cite_bounded_tail_read",
            side_effect=OSError("simulated I/O error"),
        ):
            out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        reason = out.get("reason", "")
        self.assertIn("fail-CLOSED", reason)
        self.assertIn("read failed", reason)
        self.assertEqual(self._audit_events("fact_gate_released"), [])
        denied = self._audit_events("fact_gate_denied")
        self.assertEqual(denied[-1].get("cite_status"), "verify_failed")

    def test_fabricated_citation_blocks(self):
        """REQUIRED fixture (item 6b): a citation whose text is NOT in the
        transcript BLOCKS the retry (fail-CLOSED)."""
        tp = self._write_transcript("a completely different instruction line")
        self._run_main(_CMD_PLAIN, transcript_path=str(tp))  # deny once
        out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("VERBATIM", out.get("reason", ""))
        self.assertEqual(self._audit_events("fact_gate_released"), [])

    def test_malformed_citation_on_retry_states_the_problem(self):
        self._run_main(_CMD_PLAIN)
        cmd = "CEO_DESTRUCTIVE_CITE='transcript:short' " + _CMD_PLAIN
        out, _err = self._run_main(cmd)
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("malformed", out.get("reason", ""))

    def test_deny_reason_byte_identical_n1_vs_n100(self):
        """A10 CI positive control: the ENFORCE deny message for identical
        input carries no ordinal/timestamp — byte-identical at N=1 vs
        N=100."""
        reasons = set()
        with mock.patch.object(cbs, "_audit_emit", None):  # speed: skip emits
            for _ in range(100):
                out, _err = self._run_main(_CMD_PLAIN)
                reasons.add(out.get("reason"))
        self.assertEqual(len(reasons), 1)

    def test_enforce_supersedes_pilot_gate(self):
        # Pilot armed + enforce active: the pilot's first-attempt allow path
        # must NOT undercut deny-once.
        tp = self._write_transcript(_CITED)
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {"CEO_DESTRUCTIVE_CITATION_GATE": "1"},
        ):
            out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
            self.assertEqual(out.get("decision"), "block")
            self.assertIn("FACT GATE", out.get("reason", ""))
            # ...and the deny-once release path still works under the pilot.
            out2, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
            self.assertEqual(out2, {})
        self.assertEqual(
            self._audit_events("destructive_citation_accepted"), []
        )  # the pilot never ran while enforce was active

    def test_canonical_block_never_fact_gated(self):
        # The gate keys off Decision.destructive ONLY (scope guard).
        out, _err = self._run_main("tee .claude/settings.json")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("GOVERNANCE", out.get("reason", ""))
        self.assertNotIn("FACT GATE", out.get("reason", ""))
        self.assertEqual(self._audit_events("fact_gate_denied"), [])

    def test_state_infrastructure_failure_keeps_blocking(self):
        # State-load crash degrades toward MORE blocking (no readable prior
        # => no release), never an allow.
        tp = self._write_transcript(_CITED)
        self._run_main(_CMD_PLAIN, transcript_path=str(tp))
        with mock.patch.object(
            cbs, "_fact_gate_load", side_effect=OSError("state unreadable")
        ):
            out, _err = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")


# ---------------------------------------------------------------------------
# Governance events — activation change + A12 disabled breadcrumb.
# ---------------------------------------------------------------------------
class TestGovernanceEvents(_FactGateBase):
    def _emit_calls(self, emit, action):
        return [
            c for c in emit.call_args_list
            if c.args and c.args[0] == action
        ]

    def test_activation_change_emits_once_per_flip(self):
        with mock.patch.object(cbs._audit_emit, "emit_generic") as emit:
            self._run_main(_CMD_PLAIN)             # advisory baseline: no event
            self.assertEqual(
                self._emit_calls(emit, "fact_gate_activation_changed"), []
            )
            self._set_enforce_settings("1")
            self._run_main(_CMD_PLAIN)             # flip observed: ONE event
            self._run_main(_CMD_PLAIN)             # steady state: no new event
            on_events = self._emit_calls(emit, "fact_gate_activation_changed")
            self.assertEqual(len(on_events), 1)
            self.assertEqual(on_events[0].kwargs.get("enabled"), True)
            self.assertEqual(on_events[0].kwargs.get("source"), "settings")
            self._clear_enforce_settings()
            self._run_main(_CMD_PLAIN)             # flip back: second event
        all_events = self._emit_calls(emit, "fact_gate_activation_changed")
        self.assertEqual(len(all_events), 2)
        self.assertEqual(all_events[1].kwargs.get("enabled"), False)

    def test_env_emergency_off_breadcrumb_once_per_session(self):
        self._set_enforce_settings("1")
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, {"CEO_FACT_GATE_ENFORCE": "0"}
        ), mock.patch.object(cbs._audit_emit, "emit_generic") as emit:
            out, _err = self._run_main(_CMD_PLAIN)
            self.assertEqual(out.get("decision"), "block")
            self.assertNotIn("FACT GATE", out.get("reason", ""))  # advisory
            self._run_main(_CMD_PLAIN)
        crumbs = self._emit_calls(emit, "learning_rail_disabled")
        self.assertEqual(len(crumbs), 1)           # once per session (A12)
        self.assertEqual(crumbs[0].kwargs.get("rail"), "fact_gate")
        self.assertEqual(
            crumbs[0].kwargs.get("switch"), "CEO_FACT_GATE_ENFORCE"
        )


# ---------------------------------------------------------------------------
# Clock seam (A9) — injectable now_fn on the gate entry point.
# ---------------------------------------------------------------------------
class TestClockSeam(_FactGateBase):
    def test_now_fn_injectable_stamps_first_denied(self):
        decision = cbs.decide_command(_CMD_PLAIN)
        self.assertFalse(decision.allow)
        new_decision, enforce_active = cbs._apply_fact_gate(
            decision, _CMD_PLAIN, "", now_fn=lambda: 777.25
        )
        self.assertFalse(enforce_active)           # shadow default
        self.assertIs(new_decision, decision)      # shadow: untouched object
        data = json.loads(self._state_file().read_text(encoding="utf-8"))
        sha = self._expected_sha(_CMD_PLAIN)
        self.assertEqual(data["records"][sha]["first_denied_s"], 777.25)


if __name__ == "__main__":
    unittest.main()
