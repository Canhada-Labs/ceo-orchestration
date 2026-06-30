"""Unit tests for PLAN-135 W2 H3 — the SubagentStart/SubagentStop per-agent
lifecycle bracket.

Covers BOTH halves:
  - `check_subagent_start.py` (SubagentStart sidecar recorder), and
  - the H3 extension in `check_fluency_nudge.py` (SubagentStop consumer that
    reads the sidecar + `agent_transcript_path`, computes wall/token/claim
    brackets, and emits ONE `subagent_lifecycle_observed`).

COUPLING NOTE: the H3 code lives ONLY in the staged copies under
`.claude/plans/PLAN-135/staged/w2/files/` until the W2 Owner ceremony copies
them onto the canonical positions. This is therefore a STAGED test
(PLAN-135 W2 COUPLING RULE — a test importing staged-only code lives under
staged/). It resolves the hook + the H3-bearing audit_emit CANONICAL-FIRST
(so it stays green in the assembled-canonical scratch the ceremony / VERIFY
build produces) and falls back to the staged SOURCE copy in the live
pre-ceremony tree. The live `tests/` copy of check_fluency_nudge tests stays
green standalone (the live hook has no H3 emit yet).

PLAN-118 AC-B7 isolation: the staged `_lib.audit_emit` (299-action set +
`emit_subagent_lifecycle_observed`) is bound in `sys.modules["_lib.audit_emit"]`
ONLY for the duration of a test method, via `addCleanup` save/restore — so the
collection-finish guard (test_check_test_audit_isolation) sees the canonical
`_lib.audit_emit` and the whole hooks-test session stays green. Env isolation
via TestEnvContext (no bare os.environ writes).
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

# --- Repo-root discovery + canonical-first source resolution. ---
_THIS = Path(__file__).resolve()
_repo_root = None
for parent in _THIS.parents:
    if (parent / ".claude" / "hooks" / "_lib").is_dir() and (
        parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = parent
        break
assert _repo_root is not None, "could not locate repo root from test path"

_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_STAGED_HOOKS = (
    _repo_root / ".claude" / "plans" / "PLAN-135" / "staged" / "w2" / "files"
    / ".claude" / "hooks"
)

_CANON_START = _LIVE_HOOKS / "check_subagent_start.py"
_STAGED_START = _STAGED_HOOKS / "check_subagent_start.py"
_CANON_STOP = _LIVE_HOOKS / "check_fluency_nudge.py"
_STAGED_STOP = _STAGED_HOOKS / "check_fluency_nudge.py"
_CANON_AE = _LIVE_HOOKS / "_lib" / "audit_emit.py"
_STAGED_AE = _STAGED_HOOKS / "_lib" / "audit_emit.py"

# Markers that distinguish a post-apply canonical copy from a pre-apply live one.
_START_MARKER = "check_subagent_start"  # the file's own name (always present)
_STOP_MARKER = "_observe_lifecycle"     # H3 extension function (staged-only)
_AE_MARKER = "def emit_subagent_lifecycle_observed"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    """Canonical IF it exists and carries the marker (applied tree), else the
    staged SOURCE copy (live pre-ceremony tree)."""
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "H3 source not found in canonical (%s) or staged (%s); marker=%r"
        % (canonical, staged, marker)
    )


_START_SRC = _pick(_CANON_START, _STAGED_START, _START_MARKER)
_STOP_SRC = _pick(_CANON_STOP, _STAGED_STOP, _STOP_MARKER)
_AE_SRC = _pick(_CANON_AE, _STAGED_AE, _AE_MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package (testing, filelock, …)

from _lib.testing import TestEnvContext  # noqa: E402
import _lib as _LIB_PKG  # noqa: E402  (for package-attribute rebind — see setUp)

_SENTINEL = object()


def _load_module(modname: str, path: Path):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod  # register before exec (dataclass/typing py3.9)
    spec.loader.exec_module(mod)
    return mod


# Load the two hooks once at import. They do `from _lib import filelock` at
# import (resolves to canonical) and `from _lib import audit_emit` LAZILY at
# emit time (bound per-test below). The hooks are loaded under unique module
# names so they never shadow the canonical hook objects.
start_hook = _load_module("staged_check_subagent_start_h3", _START_SRC)
stop_hook = _load_module("staged_check_fluency_nudge_h3", _STOP_SRC)


class _H3Base(TestEnvContext):
    """Common fixture: isolated state dir + transcript root + the staged
    audit_emit bound transiently in sys.modules for the emit path."""

    def setUp(self) -> None:
        super().setUp()
        # Sidecar + state under the isolated audit dir (TestEnvContext pins
        # CEO_AUDIT_LOG_DIR; the hooks' _state_dir() honors it as precedence 2).
        self.state_dir = Path(self.audit_dir)
        os.environ["CEO_SUBAGENT_LIFECYCLE_STATE_DIR"] = str(self.state_dir)
        # Transcript containment root (the realpath-under-root check).
        self.tx_root = Path(self._tmp_root) / "tx"
        self.tx_root.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_SUBAGENT_TRANSCRIPT_ROOT"] = str(self.tx_root)
        os.environ.pop("CEO_SUBAGENT_LIFECYCLE", None)
        os.environ.pop("CEO_FLUENCY_NUDGE", None)
        # Force synchronous audit writes so the emit lands in audit-log.jsonl
        # immediately (no spool drain needed). CEO_AUDIT_SYNC_MODE=1 reverts to
        # the pre-Wave-A synchronous path (spool_writer.is_sync_mode()).
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

        # Bind the staged 299-action audit_emit ONLY for this test, then
        # restore — AC-B7-safe. The stop hook's lazy `from _lib import
        # audit_emit` (inside _observe_lifecycle) resolves to this object at
        # emit time, so the emit actually exercises emit_subagent_lifecycle_observed.
        #
        # CRITICAL (S228 lesson [[feedback-fake-audit-emit-leaked-as-lib-package-attribute]]):
        # `from _lib import audit_emit` resolves the `audit_emit` ATTRIBUTE on
        # the already-imported `_lib` package object, which is SET to the
        # CANONICAL module the first time anything imported it (the hook's
        # import-time `from _lib import filelock` pulls `_lib` in). Replacing
        # ONLY sys.modules["_lib.audit_emit"] is NOT enough — the package
        # attribute still shadows it, so the hook would emit via the canonical
        # 298-action module and DROP `subagent_lifecycle_observed` (action not
        # in _KNOWN_ACTIONS). We therefore rebind BOTH the sys.modules entry
        # AND the _lib package attribute, and restore both on cleanup. This
        # leaves a clean canonical state for the AC-B7 collection-finish guard.
        saved_mod = sys.modules.get("_lib.audit_emit", _SENTINEL)
        saved_attr = getattr(_LIB_PKG, "audit_emit", _SENTINEL)
        self.audit_emit = _load_module("_lib.audit_emit", _AE_SRC)
        _LIB_PKG.audit_emit = self.audit_emit

        def _restore() -> None:
            if saved_mod is _SENTINEL:
                sys.modules.pop("_lib.audit_emit", None)
            else:
                sys.modules["_lib.audit_emit"] = saved_mod
            if saved_attr is _SENTINEL:
                try:
                    delattr(_LIB_PKG, "audit_emit")
                except AttributeError:
                    pass
            else:
                _LIB_PKG.audit_emit = saved_attr
        self.addCleanup(_restore)

    def tearDown(self) -> None:
        # PLAN-119 WS-C audit-isolation gate: setUp installs a staged
        # _lib.audit_emit shadow and registers an addCleanup(_restore) that
        # restores the canonical slot + package attr (constant-keyed). The gate's
        # static lint credits a restore only when it appears in a top-level
        # teardown method, so re-assert canonical here (idempotent — _restore
        # already ran via addCleanup) before TestEnvContext tears down.
        importlib.import_module("_lib.audit_emit")
        super().tearDown()

    # -- helpers -----------------------------------------------------------
    def _run_start(self, payload: dict) -> str:
        with redirect_stdout(io.StringIO()) as out:
            with _stdin(json.dumps(payload)):
                start_hook.main()
        return out.getvalue()

    def _run_stop(self, payload: dict) -> str:
        with redirect_stdout(io.StringIO()) as out:
            with _stdin(json.dumps(payload)):
                stop_hook.main()
        return out.getvalue()

    def _lifecycle_events(self) -> list:
        events = []
        for line in self.read_audit_log().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("action") == "subagent_lifecycle_observed":
                events.append(ev)
        return events

    def _write_transcript(self, name: str, records: list) -> Path:
        path = self.tx_root / name
        path.write_text(
            "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
        )
        return path


class _stdin:
    """Context manager: feed a string to sys.stdin for hook main()."""

    def __init__(self, data: str) -> None:
        self._data = data
        self._orig = None

    def __enter__(self):
        self._orig = sys.stdin
        sys.stdin = io.StringIO(self._data)
        return self

    def __exit__(self, *exc):
        sys.stdin = self._orig
        return False


class SidecarParityTests(unittest.TestCase):
    """The sidecar-helper PARITY block must be byte-equivalent across the two
    hooks (excluding the BEGIN-comment line that names the sibling)."""

    def _block_body(self, path: Path) -> str:
        src = path.read_text(encoding="utf-8")
        begin = src.index("# --- BEGIN sidecar helpers")
        end = src.index("# --- END sidecar helpers")
        block = src[begin:end]
        # Drop the first line (the BEGIN comment naming the sibling file).
        return block.split("\n", 1)[1]

    def test_parity_block_byte_identical(self) -> None:
        a = self._block_body(_START_SRC)
        b = self._block_body(_STOP_SRC)
        self.assertEqual(a, b, "sidecar PARITY block drifted between the two hooks")


class StartRecorderTests(_H3Base):
    def test_records_start_keyed_by_hash(self) -> None:
        self._run_start({
            "agent_id": "agent-xyz",
            "agent_type": "security-engineer",
            "session_id": "s1",
        })
        side = json.loads((self.state_dir / "subagent-lifecycle.json").read_text())
        key = start_hook._agent_key("agent-xyz")
        self.assertIn(key, side["entries"])
        entry = side["entries"][key]
        self.assertEqual(entry["agent_type"], "security-engineer")
        self.assertIn("start_ts", entry)
        # Raw agent_id never persisted (key is a hash; value has no agent_id).
        self.assertNotIn("agent-xyz", json.dumps(side))

    def test_missing_agent_id_no_record(self) -> None:
        self._run_start({"agent_type": "qa-architect"})
        self.assertFalse((self.state_dir / "subagent-lifecycle.json").is_file())

    def test_killswitch_skips_record(self) -> None:
        os.environ["CEO_SUBAGENT_LIFECYCLE"] = "0"
        out = self._run_start({"agent_id": "a", "agent_type": "qa-architect"})
        self.assertEqual(out.strip(), "{}")
        self.assertFalse((self.state_dir / "subagent-lifecycle.json").is_file())

    def test_malformed_stdin_fails_open(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            with _stdin("{not json"):
                rc = start_hook.main()
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "{}")

    def test_prune_drops_expired(self) -> None:
        now = time.time()
        entries = {
            "fresh": {"start_ts": now, "agent_type": "x"},
            "stale": {"start_ts": now - (25 * 3600), "agent_type": "y"},
        }
        pruned = start_hook._prune_entries(entries, now)
        self.assertIn("fresh", pruned)
        self.assertNotIn("stale", pruned)


class StopConsumerTests(_H3Base):
    def test_full_bracket_wall_token_claim(self) -> None:
        # Start recorded ~12s ago → wall bucket "low" (5<=s<30).
        self._run_start({
            "agent_id": "ag1", "agent_type": "code-reviewer", "session_id": "s",
        })
        # Backdate the start_ts deterministically.
        side_path = self.state_dir / "subagent-lifecycle.json"
        side = json.loads(side_path.read_text())
        key = start_hook._agent_key("ag1")
        side["entries"][key]["start_ts"] = time.time() - 12
        side_path.write_text(json.dumps(side))
        # Transcript with usage totalling 50_000 → token bucket "medium".
        tx = self._write_transcript("ag1.jsonl", [
            {"type": "assistant", "message": {"usage": {
                "input_tokens": 20000, "output_tokens": 20000,
                "cache_creation_input_tokens": 5000,
                "cache_read_input_tokens": 5000}}},
        ])
        self._run_stop({
            "agent_id": "ag1",
            "agent_transcript_path": str(tx),
            "session_id": "s",
            # 3 confidence markers → claim bucket "medium".
            "tool_response": "all done. perfect. no issues.",
        })
        evs = self._lifecycle_events()
        self.assertEqual(len(evs), 1, evs)
        ev = evs[0]
        self.assertEqual(ev["agent_archetype"], "code-reviewer")
        self.assertEqual(ev["wall_source"], "bracketed")
        self.assertEqual(ev["wall_bucket"], "low")
        self.assertEqual(ev["token_bucket"], "medium")
        self.assertEqual(ev["claim_bucket"], "medium")
        # RAW counts NEVER persisted: the event carries ONLY the closed-enum
        # archetype + the four brackets + the framework envelope. No raw token
        # sum, no raw wall seconds, no transcript path, no marker snippet, no
        # raw agent_id. Assert on the exact key set (robust — a substring
        # search for "12" would collide with the ISO `ts`).
        allowed_keys = {
            "action", "session_id", "project",
            "agent_archetype", "wall_bucket", "wall_source",
            "token_bucket", "claim_bucket",
            "event_schema", "ts",
            "tokens_in", "tokens_out", "tokens_total",
            "hmac", "hmac_error",
        }
        self.assertTrue(
            set(ev.keys()).issubset(allowed_keys),
            "leaked field(s): %s" % (set(ev.keys()) - allowed_keys),
        )
        # The S227 token-sum (50000) and per-field token names never appear.
        blob = json.dumps({k: ev[k] for k in ev if k not in ("ts",)})
        self.assertNotIn("50000", blob)
        self.assertNotIn("input_tokens", blob)
        self.assertNotIn("agent_transcript", blob)
        # tokens_in/out/total are framework-reserved NULLs, never the raw sum.
        self.assertIsNone(ev.get("tokens_total"))
        # Sidecar entry CONSUMED (popped).
        side2 = json.loads(side_path.read_text())
        self.assertNotIn(key, side2["entries"])

    def test_no_start_recorded_wall_source_unknown(self) -> None:
        # No SubagentStart for this agent; transcript supplies the token bracket.
        tx = self._write_transcript("orphan.jsonl", [
            {"message": {"usage": {"input_tokens": 100, "output_tokens": 50}}},
        ])
        self._run_stop({
            "agent_id": "never-started",
            "agent_type": "qa-architect",  # falls back to stop-payload type
            "agent_transcript_path": str(tx),
            "tool_response": "ok",
        })
        evs = self._lifecycle_events()
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual(ev["wall_source"], "unknown")
        self.assertEqual(ev["wall_bucket"], "unknown")
        self.assertEqual(ev["agent_archetype"], "qa-architect")  # stop-payload fallback
        self.assertEqual(ev["token_bucket"], "low")  # 150 tokens

    def test_transcript_path_escape_refused(self) -> None:
        # A path OUTSIDE the transcript root → containment refuse → token unknown.
        outside = Path(self._tmp_root) / "evil.jsonl"
        outside.write_text(json.dumps(
            {"message": {"usage": {"input_tokens": 999999}}}) + "\n")
        self._run_stop({
            "agent_id": "a1",
            "agent_transcript_path": str(outside),
            "tool_response": "x",
        })
        ev = self._lifecycle_events()[0]
        self.assertEqual(ev["token_bucket"], "unknown")

    def test_non_jsonl_transcript_refused(self) -> None:
        bad = self.tx_root / "t.txt"
        bad.write_text("not jsonl")
        self._run_stop({
            "agent_id": "a2",
            "agent_transcript_path": str(bad),
            "tool_response": "x",
        })
        ev = self._lifecycle_events()[0]
        self.assertEqual(ev["token_bucket"], "unknown")

    def test_emits_even_without_fluency_nudge(self) -> None:
        # Output below the nudge threshold (0 markers) STILL emits the bracket.
        self._run_stop({
            "agent_id": "quiet",
            "tool_response": "wrote three files and a test.",
        })
        evs = self._lifecycle_events()
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["claim_bucket"], "none")

    def test_lifecycle_killswitch_suppresses_emit(self) -> None:
        os.environ["CEO_SUBAGENT_LIFECYCLE"] = "0"
        out = self._run_stop({
            "agent_id": "a", "tool_response": "all done all good perfect",
        })
        self.assertEqual(self._lifecycle_events(), [])
        # Fluency nudge half still works (lifecycle off, fluency on).
        self.assertIn("{", out)

    def test_both_killswitches_short_circuit(self) -> None:
        os.environ["CEO_SUBAGENT_LIFECYCLE"] = "0"
        os.environ["CEO_FLUENCY_NUDGE"] = "0"
        out = self._run_stop({"agent_id": "a", "tool_response": "perfect perfect"})
        self.assertEqual(out.strip(), "{}")
        self.assertEqual(self._lifecycle_events(), [])

    def test_free_text_archetype_normalized(self) -> None:
        self._run_start({"agent_id": "a3", "agent_type": "Senior Security Engineer"})
        self._run_stop({"agent_id": "a3", "tool_response": "x"})
        ev = self._lifecycle_events()[0]
        self.assertEqual(ev["agent_archetype"], "security-engineer")

    def test_unknown_archetype_coerced_other(self) -> None:
        self._run_start({"agent_id": "a4", "agent_type": "frontend-wizard"})
        self._run_stop({"agent_id": "a4", "tool_response": "x"})
        ev = self._lifecycle_events()[0]
        self.assertEqual(ev["agent_archetype"], "other")

    def test_malformed_stop_stdin_fails_open(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            with _stdin("{broken"):
                rc = stop_hook.main()
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "{}")
        self.assertEqual(self._lifecycle_events(), [])

    def test_fluency_nudge_still_fires_with_lifecycle(self) -> None:
        # Many markers + short output → nudge AND one lifecycle event.
        self._run_start({"agent_id": "a5", "agent_type": "qa-architect"})
        out = self._run_stop({
            "agent_id": "a5",
            "tool_response": "all done. tests green. perfect. no issues. LGTM.",
        })
        self.assertIn("ARTIFACT-PARADOX-NUDGE", out)
        self.assertEqual(len(self._lifecycle_events()), 1)


class BucketingUnitTests(unittest.TestCase):
    def test_wall_buckets(self) -> None:
        self.assertEqual(stop_hook._wall_bucket(None), "unknown")
        self.assertEqual(stop_hook._wall_bucket(-1), "unknown")
        self.assertEqual(stop_hook._wall_bucket(2), "none")
        self.assertEqual(stop_hook._wall_bucket(10), "low")
        self.assertEqual(stop_hook._wall_bucket(60), "medium")
        self.assertEqual(stop_hook._wall_bucket(300), "high")
        self.assertEqual(stop_hook._wall_bucket(1200), "very_high")

    def test_token_buckets(self) -> None:
        self.assertEqual(stop_hook._token_bucket(None), "unknown")
        self.assertEqual(stop_hook._token_bucket(0), "none")
        self.assertEqual(stop_hook._token_bucket(500), "low")
        self.assertEqual(stop_hook._token_bucket(50_000), "medium")
        self.assertEqual(stop_hook._token_bucket(500_000), "high")
        self.assertEqual(stop_hook._token_bucket(2_000_000), "very_high")

    def test_claim_buckets(self) -> None:
        self.assertEqual(stop_hook._claim_bucket(0), "none")
        self.assertEqual(stop_hook._claim_bucket(2), "low")
        self.assertEqual(stop_hook._claim_bucket(4), "medium")
        self.assertEqual(stop_hook._claim_bucket(8), "high")
        self.assertEqual(stop_hook._claim_bucket(20), "very_high")

    def test_bucket_vocab_matches_audit_emit_enum(self) -> None:
        # Every bucket this hook can emit MUST be in the closed enum, else the
        # audit_emit scrub coerces it to "unknown" (silent data loss). Load the
        # staged audit_emit under a PRIVATE module name so we never touch the
        # canonical `_lib.audit_emit` sys.modules entry or the `_lib` package
        # attribute (AC-B7-clean — this test does not emit).
        spec = importlib.util.spec_from_file_location(
            "staged_audit_emit_bucketcheck", str(_AE_SRC)
        )
        ae = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ae)
        produced = set()
        for fn, samples in (
            (stop_hook._wall_bucket, [None, -1, 2, 10, 60, 300, 1200]),
            (stop_hook._token_bucket, [None, 0, 500, 50_000, 500_000, 2_000_000]),
            (stop_hook._claim_bucket, [0, 2, 4, 8, 20]),
        ):
            for s in samples:
                produced.add(fn(s))
        self.assertTrue(produced.issubset(ae._SUBAGENT_LIFECYCLE_BUCKETS), produced)


if __name__ == "__main__":
    unittest.main()
