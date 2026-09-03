"""Integration tests for the two-source cost surface (PLAN-186 W0, AC-1b).

``ceo-cost.py`` and ``budget-summary.py`` now derive their PRIMARY totals
from the harness-native transcripts (``message.usage``) through the
``ceo-cost-transcripts.py`` instrument, and keep the audit-log rollup as a
clearly-labelled SECONDARY source. This file covers the seam:

- the instrument's programmatic API (``transcript_rollup``) reproduces the
  numbers its own CLI prints, on the SAME synthetic corpus;
- ``--source audit`` is a byte-for-byte regression against the pre-change
  rendering (frozen literal for ``ceo-cost``; recomputed-from-``rollup()``
  equality for ``budget-summary``);
- ``--source both`` (the DEFAULT) prints both blocks, with the transcript
  numbers matching the instrument;
- ``--source transcripts`` prints only the primary block;
- an unresolvable/absent transcripts root degrades to a labelled note and
  never crashes or changes the audit numbers.

Env isolation: every class subclasses ``TestEnvContext`` (HOME /
CLAUDE_PROJECT_DIR / CEO_* snapshot-restored), and the transcripts root is
injected via ``--transcripts-root`` or ``CEO_COST_TRANSCRIPTS_DIR`` — no
test ever reads the real ``~/.claude/projects/<slug>`` corpus.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load(name: str, filename: str):
    """Load a hyphenated script as a module (dataclass-safe: registered in
    ``sys.modules`` BEFORE ``exec_module``)."""
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cct = _load("ceo_cost_transcripts", "ceo-cost-transcripts.py")
cc = _load("ceo_cost", "ceo-cost.py")
bs = _load("budget_summary", "budget-summary.py")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

#: Frozen rendering of ``ceo-cost.py --log <fixture> --since all`` captured
#: on the pre-integration tree (base b6dce78). This literal is the
#: regression oracle for "--source audit prints the same numbers as before".
FROZEN_AUDIT_TEXT = (
    "since=all  by=by-model\n"
    "\n"
    "model                                spawns        in_tok      out_tok"
    "       cost\n"
    "claude-opus-5                             1       100,000       20,000"
    "      $1.00\n"
    "claude-sonnet-5                           1        50,000        5,000"
    "      $0.15\n"
    "unknown_model                             1             0            0"
    "      $0.00\n"
    "\n"
    "TOTAL: 3 spawns, 150,000 in, 25,000 out, $1.15\n"
    "\n"
    "warning: 1 spawn(s) had no tokens_in/out — cost estimate is a lower "
    "bound. See ADR-016.\n"
    "warning: 1 spawn(s) had no model field — bucketed under "
    "'unknown_model' (free). Pre-ADR-052 spawns lack this field.\n"
)

_AUDIT_ROWS: List[Dict[str, Any]] = [
    {
        "action": "agent_spawn",
        "ts": "2026-08-01T10:00:00+00:00",
        "session_id": "sess-A",
        "skill": "code-review-checklist",
        "subagent_type": "code-reviewer",
        "model": "claude-opus-5",
        "tokens_in": 100000,
        "tokens_out": 20000,
    },
    {
        "action": "agent_spawn",
        "ts": "2026-08-02T11:30:00+00:00",
        "session_id": "sess-B",
        "skill": "threat-model",
        "subagent_type": "security",
        "model": "claude-sonnet-5",
        "tokens_in": 50000,
        "tokens_out": 5000,
    },
    {
        "action": "agent_spawn",
        "ts": "2026-08-03T12:00:00+00:00",
        "session_id": "sess-B",
        "skill": "threat-model",
        "subagent_type": "security",
    },
]


def _write_audit_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in _AUDIT_ROWS:
            fh.write(json.dumps(row) + "\n")


def _assistant(
    msg_id: str,
    model: str,
    ts: str,
    inp: int,
    out: int,
    cache_read: int = 0,
    cache_5m: int = 0,
) -> Dict[str, Any]:
    return {
        "type": "assistant",
        "timestamp": ts,
        "uuid": "u-" + msg_id,
        "requestId": "r-" + msg_id,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_5m,
                "cache_creation": {
                    "ephemeral_5m_input_tokens": cache_5m,
                    "ephemeral_1h_input_tokens": 0,
                },
            },
        },
    }


#: Deterministic synthetic corpus: 1 assento turn + 2 subagent turns (one of
#: them split across two content-block lines with a PROGRESSIVE output count,
#: which the instrument's per-field-max dedup must collapse to the terminal
#: snapshot) + 1 turn on a model absent from every pricing table.
_ASSENTO_TS = "2026-08-01T09:00:00.000Z"
_SUB_TS = "2026-08-02T09:00:00.000Z"


def _write_transcripts(root: Path) -> None:
    session = "0000aaaa-1111-2222-3333-444455556666"
    root.mkdir(parents=True, exist_ok=True)
    top = root / (session + ".jsonl")
    with top.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "timestamp": _ASSENTO_TS}) + "\n")
        fh.write(
            json.dumps(
                _assistant("m-assento-1", "claude-opus-5", _ASSENTO_TS,
                           1000, 500, cache_read=200000, cache_5m=40000)
            )
            + "\n"
        )
    sub_dir = root / session / "subagents"
    sub_dir.mkdir(parents=True, exist_ok=True)
    with (sub_dir / "agent-a1.jsonl").open("w", encoding="utf-8") as fh:
        # Same message.id twice, output growing: max-per-field dedup wins.
        fh.write(
            json.dumps(_assistant("m-sub-1", "claude-sonnet-5", _SUB_TS, 2000, 100))
            + "\n"
        )
        fh.write(
            json.dumps(_assistant("m-sub-1", "claude-sonnet-5", _SUB_TS, 2000, 900))
            + "\n"
        )
        fh.write(
            json.dumps(
                _assistant("m-sub-2", "no-such-model-xyz", _SUB_TS, 7, 3)
            )
            + "\n"
        )


def _capture(fn, *a, **kw):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = fn(*a, **kw)
    return rc, out.getvalue(), err.getvalue()


class _Base(TestEnvContext):
    """Shared setUp: isolated audit fixture + isolated transcripts corpus."""

    def setUp(self) -> None:
        super().setUp()
        self.fixt = self.project_dir / "cost-fixt"
        self.audit_log = self.fixt / "audit-log.jsonl"
        _write_audit_log(self.audit_log)
        self.tx_root = self.fixt / "transcripts"
        _write_transcripts(self.tx_root)
        # Every code path under test resolves the transcripts root from this
        # env var when no explicit flag is passed — the real HOME corpus is
        # never reachable from these tests. patch.dict restores os.environ on
        # teardown (env-hygiene mandate: no bare os.environ writes).
        # Rail r3 P2-3: TestEnvContext RESTORES the ambient cost controls but
        # does not CLEAR them, and each of these changes what the two CLIs
        # print (an extra benchmarks block, an extra native block, different
        # per-model rates). A frozen-bytes regression cannot be left at the
        # mercy of the developer's shell, so they are pinned here too.
        self._tx_env = patch.dict(
            os.environ,
            {
                "CEO_COST_TRANSCRIPTS_DIR": str(self.tx_root),
                "CEO_NATIVE_USAGE_DIR": str(self.tx_root),
                "CEO_BUDGET_BENCHMARKS": "0",
                "CEO_BUDGET_NATIVE": "0",
            },
            clear=False,
        )
        self._tx_env.start()
        # patch.dict cannot DELETE a key; the pop below is undone when the
        # patch is stopped in tearDown (the idiom test_budget_summary.py
        # already uses for CEO_BUDGET_BENCHMARKS).
        os.environ.pop("CEO_COST_PRICING_JSON", None)

    def tearDown(self) -> None:
        # Rail S341 r1 [P1]: unittest runs addCleanup callbacks AFTER
        # tearDown, so stopping this patch.dict from a cleanup would
        # restore the snapshot taken INSIDE the sandbox on top of the
        # ambient environment super().tearDown() has just put back --
        # leaving HOME and CLAUDE_PROJECT_DIR pointing at a tmp tree that
        # was just deleted, for every later test in the process. Measured
        # with controls/probe-r1-p1-cleanup-order.py; the order below is
        # load-bearing, and SandboxTeardownOrderTests pins it.
        self._tx_env.stop()
        super().tearDown()


# ---------------------------------------------------------------------------
# 1. The instrument's programmatic API == its CLI
# ---------------------------------------------------------------------------


class TranscriptApiTests(_Base):
    def test_api_matches_cli_numbers(self) -> None:
        res = cct.transcript_rollup(self.tx_root, cutoff=None, by="model")
        rc, out, _ = _capture(
            cct.main,
            ["--project-dir", str(self.tx_root), "--since", "3650d", "--json"],
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["grand_total"], res["grand_total"])
        self.assertEqual(payload["by_role"], res["by_role"])
        self.assertEqual(payload["by_model"], res["by_dimension"])
        self.assertEqual(
            payload["files"], {"assento": 1, "subagent": 1}
        )

    def test_api_totals_are_exact(self) -> None:
        res = cct.transcript_rollup(self.tx_root, cutoff=None, by="model")
        g = res["grand_total"]
        # 3 unique turns after dedup (m-assento-1, m-sub-1, m-sub-2).
        self.assertEqual(g["turns"], 3)
        self.assertEqual(g["input_tokens"], 1000 + 2000 + 7)
        # m-sub-1's TERMINAL output (900), never the interim 100.
        self.assertEqual(g["output_tokens"], 500 + 900 + 3)
        self.assertEqual(g["cache_read_tokens"], 200000)
        self.assertEqual(g["cache_write_5m"], 40000)
        self.assertIn("no-such-model-xyz", res["unresolved_models"])

    def test_cutoff_is_honored(self) -> None:
        cutoff = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
        res = cct.transcript_rollup(self.tx_root, cutoff=cutoff, by="model")
        self.assertEqual(res["grand_total"]["turns"], 2)  # assento dropped
        self.assertEqual(res["by_role"].get("assento"), None)


# ---------------------------------------------------------------------------
# 2. ceo-cost.py — the three sources
# ---------------------------------------------------------------------------


class CeoCostSourceTests(_Base):
    def _run(self, argv: List[str]):
        return _capture(cc.main, argv)

    def test_source_audit_is_byte_identical_to_frozen(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all", "--source", "audit"]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, FROZEN_AUDIT_TEXT + "\n")
        self.assertNotIn("TRANSCRIPTS", out)

    def test_default_source_is_both(self) -> None:
        rc, out, _ = self._run(["--log", str(self.audit_log), "--since", "all"])
        self.assertEqual(rc, 0)
        self.assertIn("SOURCE: TRANSCRIPTS", out)
        self.assertIn("SOURCE: AUDIT LOG", out)
        # The audit block, verbatim, is still in there.
        self.assertIn(FROZEN_AUDIT_TEXT, out)
        # ...and the transcript numbers are the instrument's.
        res = cct.transcript_rollup(self.tx_root, cutoff=None, by="model")
        self.assertIn(
            "{:,}".format(int(res["grand_total"]["cache_read_tokens"])), out
        )

    def test_source_transcripts_only(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all",
             "--source", "transcripts"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("SOURCE: TRANSCRIPTS", out)
        self.assertNotIn("SOURCE: AUDIT LOG", out)
        self.assertNotIn("by=by-model", out)

    def test_source_transcripts_survives_missing_audit_log(self) -> None:
        rc, out, err = self._run(
            ["--log", str(self.fixt / "nope.jsonl"), "--since", "all",
             "--source", "transcripts"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("SOURCE: TRANSCRIPTS", out)
        self.assertNotIn("not found", err)

    def test_audit_source_still_fails_on_missing_log(self) -> None:
        rc, _, err = self._run(
            ["--log", str(self.fixt / "nope.jsonl"), "--since", "all",
             "--source", "audit"]
        )
        self.assertEqual(rc, 1)
        self.assertIn("not found", err)

    def test_absent_transcripts_root_is_a_labelled_note(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all",
             "--transcripts-root", str(self.fixt / "does-not-exist")]
        )
        self.assertEqual(rc, 0)
        self.assertIn("transcripts source UNAVAILABLE", out)
        # The secondary source is unaffected.
        self.assertIn(FROZEN_AUDIT_TEXT, out)

    def test_incomplete_scan_is_declared_not_swallowed(self) -> None:
        # Rail r1 P1-1: a corrupted line is silently dropped by scan_files();
        # the block must say the total became a LOWER BOUND.
        broken = self.tx_root / "0000bbbb-corrupt.jsonl"
        broken.write_text(
            '{"type":"assistant","message":{"usage":{"input_tokens":1}\n',
            encoding="utf-8",
        )
        got = cc.collect_transcripts(
            root_arg=str(self.tx_root), cutoff=None, bucket="by-model"
        )
        self.assertTrue(got["available"])
        self.assertTrue(got["incomplete"])
        self.assertGreaterEqual(got["scan"]["corrupted_lines"], 1)
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("INCOMPLETE SCAN", out)
        self.assertIn("LOWER BOUND", out)

    def test_assistant_line_without_usage_is_counted(self) -> None:
        # Rail r3 P1-2: the fast prefilter dropped an assistant-shaped line
        # with no `usage` substring before any counter could see it.
        drifted = self.tx_root / "0000cccc-drift.jsonl"
        drifted.write_text(
            json.dumps(
                {"type": "assistant", "timestamp": _SUB_TS,
                 "message": {"id": "m-drift", "model": "claude-opus-5",
                             "tokens": {"input": 1}}}
            )
            + "\n",
            encoding="utf-8",
        )
        got = cc.collect_transcripts(
            root_arg=str(self.tx_root), cutoff=None, bucket="by-model"
        )
        self.assertTrue(got["available"])
        self.assertTrue(got["incomplete"])
        self.assertEqual(got["scan"]["assistant_without_usage"], 1)
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all",
             "--transcripts-root", str(self.tx_root)]
        )
        self.assertIn("INCOMPLETE SCAN", out)

    def test_clean_scan_declares_nothing(self) -> None:
        got = cc.collect_transcripts(
            root_arg=str(self.tx_root), cutoff=None, bucket="by-model"
        )
        self.assertFalse(got["incomplete"])
        rc, out, _ = self._run(["--log", str(self.audit_log), "--since", "all"])
        self.assertNotIn("INCOMPLETE SCAN", out)

    def test_cross_project_pairing_is_refused(self) -> None:
        # Rail r2 P1-1: --log points the SECONDARY source at an explicit
        # path; with no explicit transcripts root the two blocks could come
        # from two different projects.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_COST_TRANSCRIPTS_DIR", None)
            rc, out, _ = self._run(
                ["--log", str(self.audit_log), "--since", "all"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("transcripts source UNAVAILABLE", out)
        self.assertIn("refusing to pair", out)
        self.assertIn(FROZEN_AUDIT_TEXT, out)

    def test_env_audit_override_also_triggers_the_pairing_check(self) -> None:
        # Rail r3 P1-1: --log is not the only carrier; CEO_AUDIT_LOG_PATH /
        # CEO_AUDIT_LOG_DIR redirect the SECONDARY ledger too.
        with patch.dict(
            os.environ,
            {
                "CEO_AUDIT_LOG_PATH": str(self.audit_log),
                "CEO_AUDIT_LOG_DIR": str(self.fixt),
            },
            clear=False,
        ):
            os.environ.pop("CEO_COST_TRANSCRIPTS_DIR", None)
            rc, out, _ = self._run(["--since", "all"])
        self.assertEqual(rc, 0)
        self.assertIn("refusing to pair", out)

    def test_transcripts_only_is_never_suppressed_by_the_pairing(self) -> None:
        # Rail r3 P1-1, the other half: under --source transcripts there is
        # no pairing, so an explicit --log must NOT suppress the only
        # requested source.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_COST_TRANSCRIPTS_DIR", None)
            rc, out, _ = self._run(
                ["--log", str(self.audit_log), "--since", "all",
                 "--source", "transcripts", "--transcripts-root",
                 str(self.tx_root)]
            )
        self.assertEqual(rc, 0)
        self.assertNotIn("refusing to pair", out)
        self.assertIn("TRANSCRIPTS TOTAL", out)

    def test_explicit_root_re_enables_the_pairing(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all",
             "--transcripts-root", str(self.tx_root)]
        )
        self.assertEqual(rc, 0)
        self.assertNotIn("refusing to pair", out)
        self.assertIn("TRANSCRIPTS TOTAL", out)

    def test_stream_with_transcripts_source_is_refused(self) -> None:
        # Rail r2 P2-1: stream mode tails the audit log only.
        rc, _, err = self._run(
            ["--log", str(self.audit_log), "--stream",
             "--source", "transcripts"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("cannot", err)

    def test_stream_under_both_warns_but_runs(self) -> None:
        with patch.dict(os.environ, {"CEO_COST_STREAMING": "0"}, clear=False):
            rc, _, err = self._run(["--log", str(self.audit_log), "--stream"])
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT log only", err)
        self.assertIn("kill-switch", err)

    def test_json_audit_shape_unchanged(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all",
             "--format", "json", "--source", "audit"]
        )
        payload = json.loads(out)
        self.assertEqual(sorted(payload.keys()),
                         ["by_day", "by_model", "by_session", "by_skill", "totals"])

    def test_json_both_keeps_audit_keys_and_adds_transcripts(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all", "--format", "json"]
        )
        payload = json.loads(out)
        self.assertEqual(payload["totals"]["spawns"], 3)
        self.assertEqual(payload["source"], "both")
        self.assertTrue(payload["transcripts"]["available"])
        self.assertEqual(payload["transcripts"]["totals"]["turns"], 3)

    def test_by_skill_falls_back_to_role_with_a_note(self) -> None:
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "all", "--by-skill"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("no skill field", out)

    def test_since_window_reaches_the_transcripts_leg(self) -> None:
        # 1h window: every synthetic turn is from 2026-08, so the primary
        # source must report zero turns while the audit leg is unaffected.
        rc, out, _ = self._run(
            ["--log", str(self.audit_log), "--since", "1h", "--format", "json"]
        )
        payload = json.loads(out)
        self.assertEqual(payload["transcripts"]["totals"]["turns"], 0)


# ---------------------------------------------------------------------------
# 3. budget-summary.py — the three sources
# ---------------------------------------------------------------------------


class BudgetSummarySourceTests(_Base):
    def _run(self, argv: List[str]):
        return _capture(bs.main, argv)

    def test_source_audit_equals_untouched_rollup_rendering(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--source", "audit"]
        )
        self.assertEqual(rc, 0)
        data = bs.rollup(audit_dir=self.fixt, plan_filter=None,
                         since=None, by_wave=False)
        data["since"] = None
        self.assertEqual(out, bs.format_human(data) + "\n")
        self.assertNotIn("TRANSCRIPTS", out)

    def test_default_source_is_both(self) -> None:
        rc, out, _ = self._run(["summary", "--audit-dir", str(self.fixt)])
        self.assertEqual(rc, 0)
        self.assertIn("SOURCE: TRANSCRIPTS", out)
        self.assertIn("FinOps summary", out)

    def test_source_transcripts_only(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--source", "transcripts"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("SOURCE: TRANSCRIPTS", out)
        self.assertNotIn("FinOps summary", out)

    def test_json_audit_shape_has_no_new_keys(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--json",
             "--source", "audit"]
        )
        payload = json.loads(out)
        self.assertNotIn("transcripts", payload)
        self.assertNotIn("source", payload)

    def test_json_both_carries_transcripts(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--json"]
        )
        payload = json.loads(out)
        self.assertEqual(payload["source"], "both")
        self.assertTrue(payload["transcripts"]["available"])
        res = cct.transcript_rollup(self.tx_root, cutoff=None, by="model")
        self.assertEqual(
            payload["transcripts"]["totals"]["output_tokens"],
            res["grand_total"]["output_tokens"],
        )

    def test_plan_id_suppresses_transcripts_under_both(self) -> None:
        # Rail r1 P1-2: the transcript corpus has no plan field, so a
        # project-wide total beside a plan-scoped audit block would be the
        # wrong number for that plan.
        rc, out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--plan-id", "PLAN-186"]
        )
        self.assertEqual(rc, 0)
        self.assertNotIn("SOURCE: TRANSCRIPTS", out)
        self.assertIn("suppressed under --plan-id", err)
        self.assertIn("FinOps summary", out)

    def test_plan_id_with_explicit_transcripts_is_a_named_refusal(self) -> None:
        rc, out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--plan-id", "PLAN-186",
             "--source", "transcripts"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("cannot be scoped", err)

    def test_validate_memory_claim_refused_under_transcripts(self) -> None:
        # Rail r2 P2-2: the claim band is about the AUDIT total; returning
        # "unknown" under --source transcripts would read as a verdict.
        rc, _, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "transcripts", "--validate-memory-claim"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("validates the AUDIT total", err)

    def test_memory_claim_block_names_its_ledger_under_both(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--validate-memory-claim"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("Memory-claim validation:", out)
        self.assertIn("validates the AUDIT total (SECONDARY)", out)

    def test_memory_claim_block_unchanged_under_audit(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--source", "audit",
             "--validate-memory-claim"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("Memory-claim validation:", out)
        self.assertNotIn("scope   :", out)

    def test_bad_source_exits_2(self) -> None:
        rc, _, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt), "--source", "nope"]
        )
        self.assertEqual(rc, 2)

    def test_absent_root_degrades(self) -> None:
        rc, out, _ = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--transcripts-root", str(self.fixt / "gone")]
        )
        self.assertEqual(rc, 0)
        self.assertIn("transcripts source UNAVAILABLE", out)
        self.assertIn("FinOps summary", out)

    def test_bare_invocation_defaults_do_not_crash(self) -> None:
        # No subcommand: main() fills the defaults by hand — the two new
        # attributes must be among them (a missing one is an AttributeError).
        with patch.dict(
            os.environ, {"CEO_AUDIT_LOG_DIR": str(self.fixt)}, clear=False
        ):
            rc, out, _ = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("FinOps summary", out)


    # --- Achado A (S341): blocos AUDIT-side descartados por NOME, nunca em
    # silencio. Um por combinacao, cada um com o controle sob --source both.
    def test_benchmarks_under_transcripts_is_named_not_swallowed(self) -> None:
        rc, out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "transcripts", "--benchmarks"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("--benchmarks is an AUDIT-side co-report", err)
        self.assertIn("dropped under --source transcripts", err)
        self.assertNotIn("Benchmark", out)

    def test_benchmarks_under_both_is_not_dropped(self) -> None:
        # Control: the note fires ONLY where the block is actually dropped.
        rc, _out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "both", "--benchmarks"]
        )
        self.assertEqual(rc, 0)
        self.assertNotIn("--benchmarks is an AUDIT-side", err)

    def test_native_under_transcripts_is_named_not_swallowed(self) -> None:
        rc, _out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "transcripts", "--native"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("--native is an AUDIT-side cross-check", err)
        self.assertIn("dropped under --source transcripts", err)

    def test_native_under_both_is_not_dropped(self) -> None:
        rc, _out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "both", "--native"]
        )
        self.assertEqual(rc, 0)
        self.assertNotIn("--native is an AUDIT-side", err)

    def test_by_wave_under_transcripts_is_named_not_swallowed(self) -> None:
        rc, _out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "transcripts", "--by-wave"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("--by-wave shapes the AUDIT rollup", err)
        self.assertIn("dropped under --source transcripts", err)

    def test_by_wave_under_both_is_not_dropped(self) -> None:
        rc, _out, err = self._run(
            ["summary", "--audit-dir", str(self.fixt),
             "--source", "both", "--by-wave"]
        )
        self.assertEqual(rc, 0)
        self.assertNotIn("--by-wave shapes", err)

    def test_env_requested_benchmarks_is_also_named(self) -> None:
        # The opt-in has TWO doors (flag and CEO_BUDGET_BENCHMARKS=1); a note
        # keyed only on the flag would swallow the env one.
        with patch.dict(os.environ, {"CEO_BUDGET_BENCHMARKS": "1"}):
            rc, _out, err = self._run(
                ["summary", "--audit-dir", str(self.fixt),
                 "--source", "transcripts"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("--benchmarks is an AUDIT-side co-report", err)


# ---------------------------------------------------------------------------
# 5. Pair-rail round 1 cures (S341)
# ---------------------------------------------------------------------------


class SandboxTeardownOrderTests(TestEnvContext):
    """r1 [P1]: an env patch must be stopped BEFORE the base teardown.

    `addCleanup` callbacks run AFTER `tearDown`, so a cleanup-stopped
    `patch.dict` restores the snapshot taken inside the sandbox on top of
    the ambient environment `TestEnvContext.tearDown()` just put back. The
    process is then left with HOME pointing at a deleted directory.
    """

    def test_base_restores_the_ambient_environment(self) -> None:
        ambient_home = os.environ.get("HOME")
        ambient_project = os.environ.get("CLAUDE_PROJECT_DIR")
        seen = {}

        class _Inner(_Base):
            def runTest(self) -> None:  # noqa: N802 - unittest protocol
                seen["home"] = os.environ.get("HOME")
                seen["root"] = os.environ.get("CEO_COST_TRANSCRIPTS_DIR")

        result = unittest.TextTestRunner(
            stream=io.StringIO(), verbosity=0
        ).run(unittest.TestSuite([_Inner()]))
        self.assertTrue(
            result.wasSuccessful(), (result.errors, result.failures)
        )
        # The nested case really was sandboxed ...
        self.assertIsNotNone(seen.get("home"))
        self.assertNotEqual(seen["home"], ambient_home)
        self.assertIsNotNone(seen.get("root"))
        # ... and the sandbox is GONE afterwards, not re-installed.
        self.assertEqual(os.environ.get("HOME"), ambient_home)
        self.assertEqual(os.environ.get("CLAUDE_PROJECT_DIR"), ambient_project)
        self.assertTrue(Path(str(os.environ.get("HOME"))).is_dir())
        self.assertNotEqual(
            os.environ.get("CEO_COST_TRANSCRIPTS_DIR"), seen["root"]
        )


class OneWallClockTests(_Base):
    def _run(self, argv: List[str]):
        return _capture(bs.main, argv)

    def test_one_wall_clock_feeds_both_ledgers(self) -> None:
        # r1 [P2]: v1 captured `_now` for the transcripts cutoff and let
        # rollup() take its own, later clock -- D10 half-delivered. The two
        # windows must be the SAME window.
        seen = {}
        real_rollup = bs.rollup
        real_collect = bs.collect_transcripts

        def _rollup(**kw):
            seen["now"] = kw.get("now")
            return real_rollup(**kw)

        def _collect(**kw):
            seen["cutoff"] = kw.get("cutoff")
            return real_collect(**kw)

        with patch.object(bs, "rollup", _rollup), patch.object(
            bs, "collect_transcripts", _collect
        ):
            rc, _out, _err = self._run(
                ["summary", "--audit-dir", str(self.fixt), "--since", "24h"]
            )
        self.assertEqual(rc, 0)
        self.assertIsNotNone(seen.get("now"), "rollup() got no explicit clock")
        self.assertIsNotNone(seen.get("cutoff"))
        self.assertEqual(seen["now"] - seen["cutoff"], timedelta(hours=24))


class AuditCarrierTests(_Base):
    """r1 [P2]: the pairing check must ask about the carriers THIS caller
    obeys. `budget-summary.default_audit_dir()` reads CEO_AUDIT_LOG_DIR and
    nothing else, so CEO_AUDIT_LOG_PATH moves nothing here.

    Rail r2 [P1]: every env change below goes through `patch.dict` --
    `check-test-env-hygiene.py` is a hard-fail gate and flags a bare
    `os.environ[...] = ...` in a test file (it caught the first draft of
    this class, 4 sites). `patch.dict` cannot DELETE a key, so the pops
    stay; they are undone by the same context manager.
    """

    def test_log_path_alone_does_not_pin_this_caller(self) -> None:
        with patch.dict(
            os.environ,
            {"CEO_AUDIT_LOG_PATH": str(self.audit_log)},
            clear=False,
        ):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            with_var = bs.default_audit_dir()
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            without_var = bs.default_audit_dir()
            # The discriminant: the var moved NOTHING for this caller.
            self.assertEqual(str(with_var), str(without_var))
        with patch.dict(
            os.environ,
            {"CEO_AUDIT_LOG_PATH": str(self.audit_log)},
            clear=False,
        ):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            self.assertFalse(bs._tx_audit_pinned(None))

    def test_log_dir_alone_still_pins_this_caller(self) -> None:
        # Control: the carrier this caller DOES obey must still pin, or the
        # cure would have removed the r3 P1-1 protection instead of aiming it.
        with patch.dict(
            os.environ, {"CEO_AUDIT_LOG_DIR": str(self.fixt)}, clear=False
        ):
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            self.assertTrue(bs._tx_audit_pinned(None))

    def test_explicit_flag_still_pins(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            self.assertTrue(bs._tx_audit_pinned(str(self.fixt)))
            self.assertFalse(bs._tx_audit_pinned(None))

    def test_instrument_default_still_reads_every_carrier(self) -> None:
        # ceo-cost.py honours BOTH carriers and passes none, so the
        # instrument's default domain must not have narrowed.
        mod = bs.load_transcripts_instrument()
        self.assertIsNotNone(mod)
        with patch.dict(
            os.environ,
            {"CEO_AUDIT_LOG_PATH": str(self.audit_log)},
            clear=False,
        ):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            self.assertTrue(mod.audit_source_is_pinned(None))
            self.assertFalse(
                mod.audit_source_is_pinned(
                    None, carriers=("CEO_AUDIT_LOG_DIR",)
                )
            )


class LegacyAuditFallbackTests(_Base):
    """r2 [P1]: `ceo-cost.default_log_path()` can fall back to the
    pre-migration LEGACY state dir when this project's scoped log does not
    exist yet. No carrier is set on that route, so a carrier-only pairing
    check waves it through and pairs another project's legacy audit history
    with THIS project's transcripts -- the mismatch D8 exists to refuse."""

    def test_out_of_project_resolution_is_a_pin(self) -> None:
        outside = self.fixt / "audit-log.jsonl"
        self.assertTrue(cc._audit_path_is_out_of_project(outside))

    def test_scoped_resolution_is_not_a_pin(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            scoped = cc._rp.runtime_state_dir() / "audit-log.jsonl"
            self.assertFalse(cc._audit_path_is_out_of_project(scoped))

    def _ambient_corpus(self) -> Path:
        """Make the AMBIENT resolver find a real corpus.

        Without this the un-cured tree answers `available: false --
        transcripts root does not exist` and never reaches the pairing at
        all: the control would be comparing two refusals for two different
        reasons instead of a pairing against its refusal.
        """
        root = cc.transcripts_root(None)
        self.assertIsNotNone(root, "ambient transcripts root did not resolve")
        root = Path(str(root))
        root.mkdir(parents=True, exist_ok=True)
        _write_transcripts(root)
        return root

    def test_legacy_fallback_refuses_the_pairing(self) -> None:
        # Behavioural leg: no carrier at all, but the RESOLVED log lives
        # outside this project's state dir.
        outside = self.fixt / "audit-log.jsonl"
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            os.environ.pop("CEO_COST_TRANSCRIPTS_DIR", None)
            self._ambient_corpus()
            with patch.object(cc, "default_log_path", lambda: outside):
                rc, out, _err = _capture(
                    cc.main, ["--source", "both", "--format", "json"]
                )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        tx = payload.get("transcripts") or {}
        self.assertFalse(
            tx.get("available"),
            "a legacy/out-of-project audit log was paired with this "
            "project's transcripts",
        )
        self.assertIn("refusing to pair", str(tx.get("reason")))

    def test_in_project_log_keeps_the_primary_block(self) -> None:
        # Reachability control for the test above: with the audit log INSIDE
        # this project there is no pairing, and the primary block renders.
        # Without this leg, a cure that suppressed EVERYTHING would pass.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            os.environ.pop("CEO_COST_TRANSCRIPTS_DIR", None)
            self._ambient_corpus()
            scoped = cc._rp.runtime_state_dir() / "audit-log.jsonl"
            scoped.parent.mkdir(parents=True, exist_ok=True)
            _write_audit_log(scoped)
            with patch.object(cc, "default_log_path", lambda: scoped):
                rc, out, _err = _capture(
                    cc.main, ["--source", "both", "--format", "json"]
                )
        self.assertEqual(rc, 0)
        tx = json.loads(out).get("transcripts") or {}
        self.assertTrue(tx.get("available"), tx.get("reason"))


# ---------------------------------------------------------------------------
# 4. Loader seam
# ---------------------------------------------------------------------------


class InstrumentLoaderTests(_Base):
    def test_both_callers_load_the_same_instrument_file(self) -> None:
        a = cc.load_transcripts_instrument()
        b = bs.load_transcripts_instrument()
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(a.__file__, b.__file__)
        self.assertEqual(
            Path(a.__file__).name, "ceo-cost-transcripts.py"
        )

    def test_root_resolution_precedence(self) -> None:
        flagged = self.fixt / "flag-root"
        self.assertEqual(
            cc.transcripts_root(str(flagged)), flagged
        )
        self.assertEqual(cc.transcripts_root(None), self.tx_root)

    def test_shared_constants_are_not_a_second_grafia(self) -> None:
        # The callers publish --source's domain and the audit banner;
        # both must come FROM the instrument, never a local literal.
        self.assertEqual(cc.SOURCE_CHOICES, cct.SOURCE_CHOICES)
        self.assertEqual(bs.SOURCE_CHOICES, cct.SOURCE_CHOICES)
        self.assertEqual(cc.AUDIT_BANNER, cct.AUDIT_BANNER)
        self.assertEqual(bs.AUDIT_BANNER, cct.AUDIT_BANNER)
        self.assertEqual(cc.ROOT_ENV, cct.ROOT_ENV)
        self.assertEqual(bs.ROOT_ENV, cct.ROOT_ENV)
        self.assertEqual(cct.ROOT_ENV, "CEO_COST_TRANSCRIPTS_DIR")

    def test_collect_reports_reason_when_root_missing(self) -> None:
        # `root_arg` wins over the env var, so no os.environ mutation is
        # needed here (rail r1 P2-3: bare mutations are a hygiene violation).
        got = cc.collect_transcripts(
            root_arg=str(self.fixt / "absent"), cutoff=None, bucket="by-model"
        )
        self.assertFalse(got["available"])
        self.assertIn("does not exist", got["reason"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
