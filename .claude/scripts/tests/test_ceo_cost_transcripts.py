"""Unit tests for ceo-cost-transcripts.py (PLAN-186 W0).

Stdlib-only, pytest-collected (``.claude/scripts/tests`` is a pytest.ini
testpath). Env-isolated via ``TestEnvContext`` (PLAN-019 P1-QA-3 mandate —
``check-test-env-hygiene.py``): every test class subclasses it so HOME /
CLAUDE_PROJECT_DIR / sys.path are snapshot-restored, and no test ever
touches the real ``~/.claude/projects/<slug>`` tree — all synthetic
transcripts live under ``TestEnvContext``'s per-test tmp dir, and every
scan is pointed at it via the explicit ``--project-dir`` flag / function
argument (never the default resolver against real HOME state).
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

# ``_lib.testing`` (TestEnvContext) — same bootstrap as
# test_a4_pricing_doctrine.py / test_check_test_env_hygiene.py.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load ceo-cost-transcripts.py despite the dash in the filename.

    Registers the module in ``sys.modules`` under its own name BEFORE
    ``exec_module`` — Python 3.9's ``dataclasses`` (combined with
    ``from __future__ import annotations``) resolves a decorated class's
    module via ``sys.modules[cls.__module__]`` at class-definition time;
    skipping this step raises ``AttributeError: 'NoneType' object has no
    attribute '__dict__'`` the moment the loader hits the first
    ``@dataclass`` in the target file.
    """
    src = _REPO_ROOT / ".claude" / "scripts" / "ceo-cost-transcripts.py"
    spec = importlib.util.spec_from_file_location("ceo_cost_transcripts", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["ceo_cost_transcripts"] = mod
    spec.loader.exec_module(mod)
    return mod


cct = _load_module()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _usage(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_5m: int = 0,
    cache_1h: int = 0,
) -> Dict[str, Any]:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_5m + cache_1h,
        "cache_creation": {
            "ephemeral_5m_input_tokens": cache_5m,
            "ephemeral_1h_input_tokens": cache_1h,
        },
    }


def _assistant_line(
    *,
    msg_id: str,
    model: str,
    ts: datetime,
    usage: Dict[str, Any],
    session_id: str,
    is_sidechain: bool = False,
    effort: Optional[str] = "high",
    request_id: Optional[str] = None,
    extra_top: Optional[Dict[str, Any]] = None,
) -> str:
    rec: Dict[str, Any] = {
        "type": "assistant",
        "isSidechain": is_sidechain,
        "timestamp": _iso(ts),
        "sessionId": session_id,
        "requestId": request_id or ("req_" + msg_id),
        "uuid": msg_id + "-line",
        "effort": effort,
        "message": {
            "model": model,
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "x"}],
            "usage": usage,
        },
    }
    if extra_top:
        rec.update(extra_top)
    return json.dumps(rec)


class NormalizeAndPricingTests(TestEnvContext):
    def test_normalize_model_id_strips_bracket_suffix(self):
        self.assertEqual(cct.normalize_model_id("claude-fable-5[1m]"), "claude-fable-5")
        self.assertEqual(cct.normalize_model_id("claude-opus-5"), "claude-opus-5")

    def test_normalize_model_id_none_or_empty(self):
        self.assertIsNone(cct.normalize_model_id(None))
        self.assertIsNone(cct.normalize_model_id(""))
        self.assertIsNone(cct.normalize_model_id("   "))

    def test_parse_cost_table_yaml_extracts_rates_ignores_other_fields(self):
        text = (
            "schema_version: \"1.0\"\n"
            "default_model: claude-sonnet-4-6\n"
            "models:\n"
            "  claude-sonnet-5:\n"
            "    input_per_mtok: 3.00\n"
            "    output_per_mtok: 15.00  # inline comment\n"
            "    tier: sonnet\n"
            "    source_url: \"https://example.com\"  # has a # in it too\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n"
            "\n"
            "parallel_ceiling:\n"
            "  max_parallel: 6\n"
        )
        parsed = cct._parse_cost_table_yaml(text)
        self.assertEqual(parsed["claude-sonnet-5"]["input_per_mtok"], 3.00)
        self.assertEqual(parsed["claude-sonnet-5"]["output_per_mtok"], 15.00)
        self.assertEqual(parsed["claude-haiku-4-5"]["input_per_mtok"], 1.00)
        # `tier` / `source_url` / top-level scalars never leak into the rate dict
        self.assertNotIn("tier", parsed["claude-sonnet-5"])
        self.assertNotIn("max_parallel", parsed)

    def test_load_pricing_missing_file_falls_back_to_embedded(self):
        result = cct.load_pricing(str(self.project_dir / "does-not-exist.yaml"))
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.table, cct._EMBEDDED_PRICING)
        self.assertIn("embedded", result.source)

    def _default_table(self, body: str):
        """Run load_pricing(None) against a SYNTHETIC default table.

        `_SCRIPT_DIR` is read at call time, so pointing it at the tmp dir
        makes `pricing_arg=None` resolve there: the DEFAULT-path branch
        runs, without the test depending on what the real in-tree
        cost-table.yaml happens to say today.
        """
        (self.project_dir / "cost-table.yaml").write_text(
            body, encoding="utf-8"
        )
        with mock.patch.object(cct, "_SCRIPT_DIR", self.project_dir):
            return cct.load_pricing(None)

    def test_default_table_with_stale_row_gets_the_ratified_correction(self):
        # Achado B (S341): the correction exists for THIS case -- a default
        # table whose row differs from the ratified rate.
        result = self._default_table(
            "models:\n"
            "  claude-sonnet-5:\n"
            "    input_per_mtok: 3.00\n"
            "    output_per_mtok: 15.00\n"
        )
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 2.00)
        self.assertEqual(result.table["claude-sonnet-5"]["output_per_mtok"], 10.00)
        self.assertIn(
            "ratified correction (claude-sonnet-5 -> $2/$10", result.source
        )
        self.assertNotIn("NOT needed", result.source)

    def test_default_table_already_ratified_is_not_corrected(self):
        # The S340 residual: overwriting a row that already matches printed
        # a "ratified correction" that corrected nothing, and would mask a
        # legitimate refresh of the table the day one lands.
        result = self._default_table(
            "models:\n"
            "  claude-sonnet-5:\n"
            "    input_per_mtok: 2.00\n"
            "    output_per_mtok: 10.00\n"
        )
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 2.00)
        self.assertIn(
            "ratified correction NOT needed for claude-sonnet-5", result.source
        )
        self.assertNotIn("ratified correction (", result.source)

    def test_refreshed_default_table_is_not_masked(self):
        # The consequence the gate exists for: a table refreshed to a NEW
        # rate is still corrected while the override IS the ratified
        # truth -- and the source NAMES what it did, so a stale override
        # is visible instead of silent.
        result = self._default_table(
            "models:\n"
            "  claude-sonnet-5:\n"
            "    input_per_mtok: 2.50\n"
            "    output_per_mtok: 12.50\n"
        )
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 2.00)
        self.assertIn("ratified correction (claude-sonnet-5", result.source)

    def test_in_tree_default_table_is_already_ratified(self):
        # Ties the prose to the tree: since b6dce78 the shipped
        # cost-table.yaml carries the ratified row, so the real default
        # path takes the no-op branch. If this ever flips, the docstring
        # and the epilog are wrong again and this test says so.
        result = cct.load_pricing(None)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 2.00)
        self.assertIn("NOT needed", result.source)

    def test_load_pricing_explicit_path_not_overridden(self):
        custom = self.project_dir / "custom-pricing.yaml"
        custom.write_text(
            "models:\n"
            "  claude-sonnet-5:\n"
            "    input_per_mtok: 9.00\n"
            "    output_per_mtok: 99.00\n",
            encoding="utf-8",
        )
        result = cct.load_pricing(str(custom))
        self.assertFalse(result.used_fallback)
        # explicit path is trusted AS-IS — no ratified correction applied
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 9.00)
        self.assertEqual(result.table["claude-sonnet-5"]["output_per_mtok"], 99.00)
        self.assertNotIn("ratified correction", result.source)


class ExtractRecordTests(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.counters = cct.ScanCounters()
        self.now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_assento_sidechain_line_is_skipped(self):
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1",
                model="claude-opus-5",
                ts=self.now,
                usage=_usage(input_tokens=10, output_tokens=5),
                session_id="s1",
                is_sidechain=True,
            )
        )
        rec = cct._extract_record(obj, "assento", "s1", self.counters)
        self.assertIsNone(rec)
        self.assertEqual(self.counters.sidechain_in_toplevel_skipped, 1)

    def test_subagent_role_ignores_sidechain_flag(self):
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1",
                model="claude-opus-5",
                ts=self.now,
                usage=_usage(input_tokens=10, output_tokens=5),
                session_id="s1",
                is_sidechain=True,
            )
        )
        rec = cct._extract_record(obj, "subagent", "s1", self.counters)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.role, "subagent")

    def test_cache_creation_split_clamped_and_unattributed_goes_5m(self):
        # cache_creation_input_tokens totals 100, but the nested split
        # only accounts for 10 (1h) + 0 (5m) -> the remaining 90 must be
        # folded into the 5m bucket (mirrors budget-summary.py's
        # unattributed-write-assumed-5m reconciliation), never dropped.
        usage = {
            "input_tokens": 1,
            "output_tokens": 2,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 100,
            "cache_creation": {"ephemeral_1h_input_tokens": 10, "ephemeral_5m_input_tokens": 0},
        }
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1", model="claude-opus-5", ts=self.now, usage=usage, session_id="s1"
            )
        )
        rec = cct._extract_record(obj, "assento", "s1", self.counters)
        self.assertEqual(rec.cache_write_1h, 10)
        self.assertEqual(rec.cache_write_5m, 90)

    def test_missing_timestamp_is_counted_not_raised(self):
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1",
                model="claude-opus-5",
                ts=self.now,
                usage=_usage(input_tokens=1),
                session_id="s1",
            )
        )
        obj["timestamp"] = "not-a-timestamp"
        rec = cct._extract_record(obj, "assento", "s1", self.counters)
        self.assertIsNone(rec)
        self.assertEqual(self.counters.missing_timestamp, 1)

    def test_unresolvable_model_id_is_tagged_not_dropped(self):
        # An id syntactically fine but absent from the active pricing
        # table is NOT resolved at extraction time (normalize_model_id
        # only strips a trailing [..] suffix, it does not validate table
        # membership) — "unresolved" is a PRICING-time concept, surfaced
        # via Priced.resolved, never invented as a fabricated $0 cost.
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1",
                model="claude-not-a-real-model",
                ts=self.now,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="s1",
            )
        )
        rec = cct._extract_record(obj, "assento", "s1", self.counters)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.model, "claude-not-a-real-model")
        priced = cct.price_records([rec], cct._EMBEDDED_PRICING)
        self.assertEqual(len(priced), 1)
        self.assertFalse(priced[0].resolved)
        self.assertEqual(priced[0].cost_usd, 0.0)

    def test_missing_model_field_is_tagged_unresolved_in_place(self):
        obj = json.loads(
            _assistant_line(
                msg_id="msg_1",
                model="claude-opus-5",
                ts=self.now,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="s1",
            )
        )
        obj["message"]["model"] = None
        rec = cct._extract_record(obj, "assento", "s1", self.counters)
        self.assertIsNotNone(rec)
        self.assertIn("unresolved", rec.model)


class ScanFilesAndDedupTests(TestEnvContext):
    """Builds a small synthetic corpus: one top-level (assento) session
    file with a duplicated content-block message + one embedded sidechain
    line, and one subagent transcript file — then exercises the full
    discover -> scan -> dedup -> price -> aggregate pipeline with a KNOWN
    price table (positive control: exact expected total in cents)."""

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        self.t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

        # --- top-level assento file: session "sess-a" ---
        top = self.corpus / "sess-a.jsonl"
        usage_a = _usage(input_tokens=1000, output_tokens=200, cache_read=500, cache_5m=300, cache_1h=100)
        lines = [
            # two content-block lines for the SAME message -> must dedup to ONE
            _assistant_line(
                msg_id="msg_dup", model="claude-opus-5", ts=self.t0, usage=usage_a, session_id="sess-a"
            ),
            _assistant_line(
                msg_id="msg_dup", model="claude-opus-5", ts=self.t0, usage=usage_a, session_id="sess-a"
            ),
            # a genuinely distinct message
            _assistant_line(
                msg_id="msg_two",
                model="claude-opus-5",
                ts=self.t0 + timedelta(minutes=1),
                usage=_usage(input_tokens=10, output_tokens=5),
                session_id="sess-a",
            ),
            # a sidechain line embedded in the top-level file -> must be
            # SKIPPED for the assento role (would double-count a Task-tool
            # sub-dispatch that also has its own agent-*.jsonl elsewhere)
            _assistant_line(
                msg_id="msg_side",
                model="claude-opus-5",
                ts=self.t0 + timedelta(minutes=2),
                usage=_usage(input_tokens=999, output_tokens=999),
                session_id="sess-a",
                is_sidechain=True,
            ),
            # a record OUTSIDE the --since window (very old)
            _assistant_line(
                msg_id="msg_old",
                model="claude-opus-5",
                ts=self.t0 - timedelta(days=400),
                usage=_usage(input_tokens=777, output_tokens=777),
                session_id="sess-a",
            ),
            # a non-assistant line -> must be ignored cleanly
            json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
            # a CORRUPTED line that still matches the fast pre-filter
            # substrings (contains "assistant" and "usage") but is not
            # valid JSON -> negative control, must be counted & skipped
            '{"type": "assistant", "message": {"usage": {"input_tokens": 5 BROKEN',
        ]
        top.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # --- subagent transcript: parent session "sess-a", agent "aX" ---
        sub_dir = self.corpus / "sess-a" / "subagents"
        sub_dir.mkdir(parents=True, exist_ok=True)
        sub_file = sub_dir / "agent-aX.jsonl"
        usage_sub = _usage(input_tokens=50, output_tokens=25, cache_read=10)
        sub_file.write_text(
            _assistant_line(
                msg_id="msg_sub1",
                model="claude-sonnet-5",
                ts=self.t0 + timedelta(minutes=1),
                usage=usage_sub,
                session_id="sess-a",
                is_sidechain=True,  # subagent transcripts are always sidechain
            )
            + "\n",
            encoding="utf-8",
        )

        # A flat cost-table for exact-cent positive control.
        self.pricing = {
            "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
            "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
        }

    def test_discover_files_finds_both_trees(self):
        top, sub = cct.discover_files(self.corpus)
        self.assertEqual([p.name for p in top], ["sess-a.jsonl"])
        self.assertEqual(len(sub), 1)
        self.assertTrue(sub[0].name.startswith("agent-"))

    def test_full_pipeline_dedup_sidechain_skip_window_and_cost(self):
        counters = cct.ScanCounters()
        top, sub = cct.discover_files(self.corpus)
        records = cct.scan_files(top, "assento", self.corpus, counters)
        records += cct.scan_files(sub, "subagent", self.corpus, counters)

        # --since-style window: keep only the last 30 days from "now"
        # pinned at self.t0 + a few minutes (deterministic, no real clock).
        cutoff = self.t0 - timedelta(days=30)
        records = [r for r in records if r.ts >= cutoff]

        deduped, dropped = cct.dedup(records)
        self.assertEqual(dropped, 1)  # the duplicated content-block line

        priced = cct.price_records(deduped, self.pricing)
        grand, role_totals, group_totals = cct.aggregate(priced, "role")

        # Expected: msg_dup (1x, deduped) + msg_two, in assento; msg_sub1
        # in subagent. msg_side (sidechain-in-toplevel) and msg_old
        # (outside window) and the corrupted line are ALL excluded.
        self.assertEqual(int(grand["turns"]), 3)
        self.assertEqual(counters.corrupted_lines, 1)
        self.assertEqual(counters.sidechain_in_toplevel_skipped, 1)

        expected_assento_usd = (
            (1000 * 5.00 + 200 * 25.00 + 500 * 5.00 * 0.10 + 300 * 5.00 * 1.25 + 100 * 5.00 * 2.00) / 1e6
            + (10 * 5.00 + 5 * 25.00) / 1e6
        )
        expected_subagent_usd = (50 * 2.00 + 25 * 10.00 + 10 * 2.00 * 0.10) / 1e6
        self.assertAlmostEqual(role_totals["assento"]["usd"], expected_assento_usd, places=9)
        self.assertAlmostEqual(role_totals["subagent"]["usd"], expected_subagent_usd, places=9)
        self.assertAlmostEqual(grand["usd"], expected_assento_usd + expected_subagent_usd, places=9)
        # msg_old (400 days back) must never appear despite being on disk
        self.assertNotIn("msg_old", [r.key for r in deduped])


class ProgressiveUsageDedupTests(TestEnvContext):
    """Cross-model review finding (post-delivery follow-up): a
    message.id's usage snapshot is NOT always a static repeat across its
    content-block JSONL lines. Measured on the live subagent corpus:
    14,054 of 21,414 multi-line message.id groups (65.6%) carry a
    PROGRESSIVE output_tokens count growing monotonically in file order
    (0 counter-examples), input_tokens held constant across the group.
    A first-write-wins dedup keeps the SMALLEST (interim) output_tokens,
    undercounting cost. These tests pin the fix: dedup() now takes the
    per-field MAXIMUM across every line sharing a key.
    """

    def setUp(self):
        super().setUp()
        self.t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _progressive_group(self) -> List[cct.UsageRecord]:
        """Three lines of the SAME message: thinking (interim
        output=4), tool_use (output=92), final text (output=182) — the
        exact shape reported by the reviewer (interim 4 -> final 182).
        input_tokens/cache_read/cache_write held constant, as measured.
        """
        raw_lines = [
            _assistant_line(
                msg_id="msg_progressive",
                model="claude-opus-5",
                ts=self.t0,
                usage=_usage(input_tokens=200, output_tokens=out, cache_read=1000, cache_5m=50),
                session_id="sess-p",
            )
            for out in (4, 92, 182)
        ]
        counters = cct.ScanCounters()
        recs = []
        for raw in raw_lines:
            rec = cct._extract_record(json.loads(raw), "subagent", "sess-p", counters)
            self.assertIsNotNone(rec)
            recs.append(rec)
        return recs

    def test_dedup_takes_terminal_max_output_not_first_write(self):
        recs = self._progressive_group()
        # Sanity: all three share ONE dedup key (that's the bug's precondition).
        self.assertEqual(len({r.key for r in recs}), 1)

        deduped, dropped = cct.dedup(recs)
        self.assertEqual(dropped, 2)
        self.assertEqual(len(deduped), 1)
        merged = deduped[0]
        # THE fix: output_tokens must be the TERMINAL/max value (182),
        # never the first-write-wins interim value (4).
        self.assertEqual(merged.output_tokens, 182)
        self.assertEqual(merged.input_tokens, 200)  # constant across the group
        self.assertEqual(merged.cache_read_tokens, 1000)
        self.assertEqual(merged.cache_write_5m, 50)
        # merged timestamp is the EARLIEST line in the group (turn start)
        self.assertEqual(merged.ts, self.t0)

    def test_dedup_positive_control_exact_cost_uses_terminal_output(self):
        recs = self._progressive_group()
        deduped, _ = cct.dedup(recs)
        pricing = {"claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00}}
        priced = cct.price_records(deduped, pricing)
        self.assertEqual(len(priced), 1)
        # 200 in @ $5/MTok + 182 out @ $25/MTok + 1000 cache-read @ $0.50/MTok
        # + 50 cache-write-5m @ $6.25/MTok — first-write-wins would have
        # priced 4 output tokens instead of 182, undercounting by
        # (182-4)*25/1e6 = $0.00445 on this fixture.
        expected = (200 * 5.00 + 182 * 25.00 + 1000 * 5.00 * 0.10 + 50 * 5.00 * 1.25) / 1e6
        self.assertAlmostEqual(priced[0].cost_usd, expected, places=12)
        wrong_first_write_cost = (200 * 5.00 + 4 * 25.00 + 1000 * 5.00 * 0.10 + 50 * 5.00 * 1.25) / 1e6
        self.assertGreater(priced[0].cost_usd, wrong_first_write_cost)

    def test_dedup_handles_mixed_progressive_and_singleton_records(self):
        progressive = self._progressive_group()
        counters = cct.ScanCounters()
        singleton_raw = _assistant_line(
            msg_id="msg_singleton",
            model="claude-opus-5",
            ts=self.t0 + timedelta(minutes=1),
            usage=_usage(input_tokens=1, output_tokens=1),
            session_id="sess-p",
        )
        singleton = cct._extract_record(json.loads(singleton_raw), "subagent", "sess-p", counters)
        deduped, dropped = cct.dedup(progressive + [singleton])
        self.assertEqual(dropped, 2)
        self.assertEqual(len(deduped), 2)
        by_key = {r.key: r for r in deduped}
        self.assertEqual(by_key[singleton.key].output_tokens, 1)


class MainCliEndToEndTests(TestEnvContext):
    """Exercises main() as a subprocess-free CLI call (argv list),
    writing only under TestEnvContext's isolated project_dir — never the
    real ~/.claude/projects tree."""

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "native-corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc) - timedelta(hours=1)
        line = _assistant_line(
            msg_id="msg_cli_1",
            model="claude-haiku-4-5",
            ts=now,
            usage=_usage(input_tokens=1_000_000, output_tokens=1_000_000),
            session_id="cli-sess",
        )
        (self.corpus / "cli-sess.jsonl").write_text(line + "\n", encoding="utf-8")

        self.pricing_file = self.project_dir / "pricing.yaml"
        self.pricing_file.write_text(
            "models:\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n",
            encoding="utf-8",
        )

    def _run(self, extra_args: List[str]) -> str:
        buf = io.StringIO()
        argv = [
            "--project-dir",
            str(self.corpus),
            "--pricing",
            str(self.pricing_file),
        ] + extra_args
        with redirect_stdout(buf):
            rc = cct.main(argv)
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_json_output_matches_hand_computed_total(self):
        out = self._run(["--json", "--since", "24h", "--by", "model"])
        payload = json.loads(out)
        # 1,000,000 input @ $1/MTok + 1,000,000 output @ $5/MTok = $1 + $5 = $6.00
        self.assertAlmostEqual(payload["grand_total"]["usd"], 6.00, places=6)
        self.assertEqual(payload["grand_total"]["turns"], 1)
        self.assertFalse(payload["pricing_used_fallback"])

    def test_human_output_contains_totals_section(self):
        out = self._run(["--since", "24h"])
        self.assertIn("TOTAIS POR PAPEL", out)
        self.assertIn("$6.00", out)

    def test_since_window_excludes_old_record(self):
        # Same corpus, but --since 24h against a record now 400 days old.
        old_ts = datetime.now(timezone.utc) - timedelta(days=400)
        (self.corpus / "old-sess.jsonl").write_text(
            _assistant_line(
                msg_id="msg_old_cli",
                model="claude-haiku-4-5",
                ts=old_ts,
                usage=_usage(input_tokens=999, output_tokens=999),
                session_id="old-sess",
            )
            + "\n",
            encoding="utf-8",
        )
        out = self._run(["--json", "--since", "24h"])
        payload = json.loads(out)
        # old-sess must be invisible; only the 1-hour-old cli-sess record counts.
        self.assertEqual(payload["grand_total"]["turns"], 1)

    def test_invalid_since_exits_nonzero(self):
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                cct.main(["--project-dir", str(self.corpus), "--since", "not-a-window"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_missing_project_dir_exits_nonzero(self):
        missing = self.project_dir / "does-not-exist-dir"
        rc = cct.main(["--project-dir", str(missing)])
        self.assertEqual(rc, 2)


class DefaultProjectDirResolutionTests(TestEnvContext):
    """Confirms the default (--project-dir omitted) path delegates to the
    SAME single resolver as `runtime_paths.py --state-dir`, using
    TestEnvContext's isolated HOME/CLAUDE_PROJECT_DIR rather than the
    real ones."""

    def test_default_project_dir_matches_runtime_paths_resolver(self):
        from _lib import runtime_paths as rp  # already isolated via TestEnvContext's HOME/CLAUDE_PROJECT_DIR

        expected = rp.runtime_state_dir()
        got = cct._default_project_dir()
        self.assertEqual(got, expected)
        # sanity: this must live under the isolated HOME, never the real one
        self.assertTrue(str(got).startswith(str(self.home_dir)))


class WindowUpperBoundCliTests(TestEnvContext):
    """`--until` (PLAN-186 AC-1, S344): the UPPER bound of the window.

    Every assertion is about RECORD resolution -- the bound is compared
    against the same `UsageRecord.ts` the `--since` cutoff filters, and a
    record stamped exactly at it is INSIDE. All fixtures live under
    TestEnvContext's per-test tmp dir; the real corpus is never read.
    """

    #: The bound and its two neighbours, 13 ms apart -- the same shape the
    #: AC-1 measurement hit on the live corpus (last included record at
    #: ...05.807Z, next one at ...18.718Z).
    AT_BOUND = datetime(2026, 9, 2, 12, 55, 5, 807000, tzinfo=timezone.utc)
    JUST_AFTER = datetime(2026, 9, 2, 12, 55, 5, 808000, tzinfo=timezone.utc)
    BEFORE = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "window-corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        rows = [
            ("msg_before", self.BEFORE, 1_000_000, 0),
            ("msg_at_bound", self.AT_BOUND, 0, 1_000_000),
            ("msg_after", self.JUST_AFTER, 0, 2_000_000),
        ]
        (self.corpus / "win-sess.jsonl").write_text(
            "\n".join(
                _assistant_line(
                    msg_id=mid,
                    model="claude-haiku-4-5",
                    ts=ts,
                    usage=_usage(input_tokens=inp, output_tokens=outp),
                    session_id="win-sess",
                )
                for mid, ts, inp, outp in rows
            )
            + "\n",
            encoding="utf-8",
        )
        self.pricing_file = self.project_dir / "pricing.yaml"
        self.pricing_file.write_text(
            "models:\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n",
            encoding="utf-8",
        )

    def _json(self, extra: List[str]) -> Dict[str, Any]:
        buf = io.StringIO()
        argv = [
            "--project-dir",
            str(self.corpus),
            "--pricing",
            str(self.pricing_file),
            "--json",
            # wide enough that the fixture's 2026-09-02 stamps are inside
            # the lower bound no matter when the suite runs.
            "--since",
            "36500d",
        ] + extra
        with redirect_stdout(buf):
            rc = cct.main(argv)
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def _exit_code(self, extra: List[str]) -> int:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                with mock.patch.object(sys, "stderr", err):
                    cct.main(
                        ["--project-dir", str(self.corpus), "--json"] + extra
                    )
        self.last_stderr = err.getvalue()
        return ctx.exception.code

    def test_no_until_sees_the_whole_corpus(self):
        payload = self._json([])
        self.assertEqual(payload["grand_total"]["turns"], 3)
        self.assertIsNone(payload["until"])

    def test_until_is_inclusive_at_the_record(self):
        # The bound IS a record's own stamp: that record is inside, the
        # next one (1 ms later) is outside. Resolution is the record's,
        # not a grid's.
        payload = self._json(["--until", "2026-09-02T12:55:05.807Z"])
        self.assertEqual(payload["grand_total"]["turns"], 2)
        # 1,000,000 input @ $1 + 1,000,000 output @ $5 = $6.00
        self.assertAlmostEqual(payload["grand_total"]["usd"], 6.00, places=6)
        self.assertEqual(payload["until"], "2026-09-02T12:55:05.807Z")

    def test_until_excludes_a_record_after_the_bound(self):
        payload = self._json(["--until", "2026-09-02T12:00:00Z"])
        self.assertEqual(payload["grand_total"]["turns"], 1)
        self.assertAlmostEqual(payload["grand_total"]["usd"], 1.00, places=6)

    def test_until_accepts_an_explicit_offset_and_a_naive_value(self):
        offset = self._json(["--until", "2026-09-02T12:55:05.807+00:00"])
        naive = self._json(["--until", "2026-09-02T12:55:05.807"])
        self.assertEqual(offset["grand_total"]["turns"], 2)
        self.assertEqual(naive["grand_total"]["turns"], 2)

    def test_until_filters_the_same_field_the_since_cutoff_does(self):
        # Both bounds are applied to UsageRecord.ts by the ONE pipeline:
        # a lower bound just above the first record and an upper bound at
        # the second leave exactly the second record.
        res = cct.transcript_rollup(
            self.corpus,
            cutoff=self.AT_BOUND,
            until=self.AT_BOUND,
            pricing_arg=str(self.pricing_file),
            by="model",
        )
        self.assertEqual(res["grand_total"]["turns"], 1)
        self.assertAlmostEqual(res["grand_total"]["usd"], 5.00, places=6)

    def test_malformed_until_is_refused_by_name_with_rc_2(self):
        for bad in ("not-a-date", "2026-13-02T00:00:00Z", "yesterday", ""):
            with self.subTest(bad=bad):
                code = self._exit_code(["--since", "36500d", "--until", bad])
                self.assertEqual(code, 2)

    def test_until_before_the_since_cutoff_is_refused_by_name(self):
        code = self._exit_code(["--since", "24h", "--until", "2020-01-01T00:00:00Z"])
        self.assertEqual(code, 2)
        self.assertIn("does not follow the window's LOWER bound", self.last_stderr)
        # the refusal NAMES the moving bound it computed, not just the flag
        self.assertIn("--since 24h", self.last_stderr)

    def test_human_report_names_the_upper_bound(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cct.main(
                [
                    "--project-dir",
                    str(self.corpus),
                    "--pricing",
                    str(self.pricing_file),
                    "--since",
                    "36500d",
                    "--until",
                    "2026-09-02T12:55:05.807Z",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn("2026-09-02T12:55:05.807Z", buf.getvalue())


class MultiDimensionBreakdownTests(TestEnvContext):
    """`--by role,model` (PLAN-186 AC-1, S344): the two-dimension cut the
    published reference table is written in. Grouping ORDER is the order
    given, and the groups partition the ungrouped total exactly."""

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "cut-corpus"
        (self.corpus / "cut-sess" / "subagents").mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc) - timedelta(hours=1)
        (self.corpus / "cut-sess.jsonl").write_text(
            _assistant_line(
                msg_id="msg_seat_a",
                model="claude-haiku-4-5",
                ts=now,
                usage=_usage(input_tokens=1_000_000),
                session_id="cut-sess",
            )
            + "\n"
            + _assistant_line(
                msg_id="msg_seat_b",
                model="claude-opus-5",
                ts=now,
                usage=_usage(input_tokens=2_000_000),
                session_id="cut-sess",
            )
            + "\n",
            encoding="utf-8",
        )
        (self.corpus / "cut-sess" / "subagents" / "agent-1.jsonl").write_text(
            _assistant_line(
                msg_id="msg_sub_a",
                model="claude-haiku-4-5",
                ts=now,
                usage=_usage(input_tokens=4_000_000),
                session_id="cut-sess",
            )
            + "\n",
            encoding="utf-8",
        )
        self.pricing_file = self.project_dir / "pricing.yaml"
        self.pricing_file.write_text(
            "models:\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n"
            "  claude-opus-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n",
            encoding="utf-8",
        )

    def _json(self, by: str) -> Dict[str, Any]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cct.main(
                [
                    "--project-dir",
                    str(self.corpus),
                    "--pricing",
                    str(self.pricing_file),
                    "--json",
                    "--since",
                    "24h",
                    "--by",
                    by,
                ]
            )
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_grouping_order_follows_the_flag(self):
        role_first = set(self._json("role,model")["by_role,model"])
        model_first = set(self._json("model,role")["by_model,role"])
        self.assertEqual(
            role_first,
            {
                "assento | claude-haiku-4-5",
                "assento | claude-opus-5",
                "subagent | claude-haiku-4-5",
            },
        )
        self.assertEqual(
            model_first,
            {
                "claude-haiku-4-5 | assento",
                "claude-opus-5 | assento",
                "claude-haiku-4-5 | subagent",
            },
        )

    def test_group_totals_equal_the_ungrouped_total(self):
        payload = self._json("role,model")
        groups = payload["by_role,model"]
        grand = payload["grand_total"]
        self.assertAlmostEqual(
            sum(g["usd"] for g in groups.values()), grand["usd"], places=6
        )
        self.assertEqual(sum(g["turns"] for g in groups.values()), grand["turns"])
        for cls in cct._TOKEN_CLASSES:
            self.assertEqual(
                sum(g[cls] for g in groups.values()), grand[cls], msg=cls
            )

    def test_single_dimension_is_unchanged(self):
        payload = self._json("model")
        self.assertEqual(
            set(payload["by_model"]), {"claude-haiku-4-5", "claude-opus-5"}
        )

    def test_split_by_preserves_order_and_refuses_by_name(self):
        self.assertEqual(cct._split_by("role,model"), ["role", "model"])
        self.assertEqual(cct._split_by("model, role"), ["model", "role"])
        self.assertEqual(cct._split_by("day"), ["day"])
        for bad, needle in (
            ("role,nope", "unknown breakdown dimension"),
            ("role,", "empty dimension"),
            (",model", "empty dimension"),
            ("role,role", "duplicated dimension"),
            ("", "empty --by value"),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    cct._split_by(bad)
                self.assertIn(needle, str(ctx.exception))

    def test_composite_label_is_injective_when_a_value_holds_the_separator(self):
        # Rail r1 [P2]: a raw join would merge the tuples ('a | b', 'c')
        # and ('a', 'b | c') into one bucket. Session ids come from the
        # corpus, not from a flag, so the label must be injective by
        # CONSTRUCTION rather than by an assumption about the values.
        class _Rec(object):
            def __init__(self, session_id, model):
                self.session_id = session_id
                self.model = model

        class _Priced(object):
            def __init__(self, rec):
                self.rec = rec

        key = cct._group_key_fn(["session", "model"])
        left = key(_Priced(_Rec("a | b", "c")))
        right = key(_Priced(_Rec("a", "b | c")))
        self.assertNotEqual(left, right)
        # and a value with no separator is untouched
        self.assertEqual(
            key(_Priced(_Rec("sess-1", "claude-opus-5"))),
            "sess-1 | claude-opus-5",
        )

    def test_malformed_by_exits_2_without_falling_back_to_one_dimension(self):
        for bad in ("role,nope", "role,", "role,role", ""):
            with self.subTest(bad=bad):
                err = io.StringIO()
                with self.assertRaises(SystemExit) as ctx:
                    with redirect_stdout(io.StringIO()):
                        with mock.patch.object(sys, "stderr", err):
                            cct.main(
                                [
                                    "--project-dir",
                                    str(self.corpus),
                                    "--by",
                                    bad,
                                ]
                            )
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("invalid --by", err.getvalue())

    def test_a_repeated_by_flag_is_refused_by_name(self):
        # Rail r4 [P1]: with argparse's default `store` action,
        # `--by role --by model` kept only the LAST value and grouped by
        # ONE dimension, silently dropping `role` -- contradicting the
        # help's promise. `action="append"` turns that into a refusal.
        err = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                with mock.patch.object(sys, "stderr", err):
                    cct.main(
                        [
                            "--project-dir",
                            str(self.corpus),
                            "--by",
                            "role",
                            "--by",
                            "model",
                        ]
                    )
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn(
            "pass ONE --by with a comma-separated list", err.getvalue()
        )
        # and the single comma-separated form still cuts both dimensions,
        # with the groups still partitioning the ungrouped total
        payload = self._json("role,model")
        groups = payload["by_role,model"]
        self.assertEqual(len(groups), 3)
        self.assertEqual(
            sum(g["turns"] for g in groups.values()),
            payload["grand_total"]["turns"],
        )


class AbsoluteLowerBoundCliTests(TestEnvContext):
    """`--since-at` (PLAN-186 AC-1, rail r4): the ABSOLUTE lower bound.

    `--since` is measured back from the wall clock, so a command
    DOCUMENTED as a closed window selects a different set of records on a
    later run -- the reproduction in docs/cost-of-operation.md was not
    literally re-runnable. `--since-at` fixes the lower end to an instant
    at the SAME record resolution as `--until`. Fixtures live under
    TestEnvContext's per-test tmp dir; the real corpus is never read.
    """

    #: Three records, 1 ms apart, around the bound.
    LO = datetime(2026, 9, 2, 12, 55, 5, 806000, tzinfo=timezone.utc)
    MID = datetime(2026, 9, 2, 12, 55, 5, 807000, tzinfo=timezone.utc)
    HI = datetime(2026, 9, 2, 12, 55, 5, 808000, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "lower-corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        rows = [
            ("msg_lo", self.LO, 100),
            ("msg_mid", self.MID, 200),
            ("msg_hi", self.HI, 400),
        ]
        (self.corpus / "low-sess.jsonl").write_text(
            "\n".join(
                _assistant_line(
                    msg_id=mid,
                    model="claude-haiku-4-5",
                    ts=ts,
                    usage=_usage(input_tokens=0, output_tokens=outp),
                    session_id="low-sess",
                )
                for mid, ts, outp in rows
            )
            + "\n",
            encoding="utf-8",
        )
        self.pricing_file = self.project_dir / "pricing.yaml"
        self.pricing_file.write_text(
            "models:\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n",
            encoding="utf-8",
        )

    def _json(self, extra: List[str]) -> Dict[str, Any]:
        buf = io.StringIO()
        argv = [
            "--project-dir",
            str(self.corpus),
            "--pricing",
            str(self.pricing_file),
            "--json",
        ] + extra
        with redirect_stdout(buf):
            rc = cct.main(argv)
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def _exit_code(self, extra: List[str]) -> int:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                with mock.patch.object(sys, "stderr", err):
                    cct.main(
                        ["--project-dir", str(self.corpus), "--json"] + extra
                    )
        self.last_stderr = err.getvalue()
        return ctx.exception.code

    def test_since_at_is_inclusive_at_the_record(self):
        # The bound IS the middle record's own stamp: that record is IN,
        # the one 1 ms earlier is OUT. Same resolution as --until.
        payload = self._json(["--since-at", "2026-09-02T12:55:05.807Z"])
        self.assertEqual(payload["grand_total"]["turns"], 2)
        self.assertEqual(payload["grand_total"]["output_tokens"], 600)
        self.assertEqual(payload["since_at"], "2026-09-02T12:55:05.807Z")
        # the relative bound is reported ABSENT, not as the unused 30d
        self.assertIsNone(payload["since"])

    def test_since_at_one_millisecond_earlier_admits_the_first_record(self):
        payload = self._json(["--since-at", "2026-09-02T12:55:05.806Z"])
        self.assertEqual(payload["grand_total"]["turns"], 3)
        self.assertEqual(payload["grand_total"]["output_tokens"], 700)

    def test_since_at_after_the_last_record_selects_nothing(self):
        payload = self._json(["--since-at", "2026-09-02T12:55:05.809Z"])
        self.assertEqual(payload["grand_total"]["turns"], 0)

    def test_since_at_accepts_an_explicit_offset_and_a_naive_value(self):
        offset = self._json(["--since-at", "2026-09-02T12:55:05.807+00:00"])
        naive = self._json(["--since-at", "2026-09-02T12:55:05.807"])
        self.assertEqual(offset["grand_total"]["turns"], 2)
        self.assertEqual(naive["grand_total"]["turns"], 2)

    def test_closed_absolute_window_isolates_one_record(self):
        # [.807, .807999] holds the middle record ALONE, and both ends are
        # absolute: re-running this command tomorrow selects the same
        # record -- the property `--since` cannot offer.
        payload = self._json(
            [
                "--since-at",
                "2026-09-02T12:55:05.807Z",
                "--until",
                "2026-09-02T12:55:05.807999Z",
            ]
        )
        self.assertEqual(payload["grand_total"]["turns"], 1)
        self.assertEqual(payload["grand_total"]["output_tokens"], 200)

    def test_since_and_since_at_together_are_refused_by_name(self):
        code = self._exit_code(
            ["--since", "36500d", "--since-at", "2026-09-02T00:00:00Z"]
        )
        self.assertEqual(code, 2)
        self.assertIn("--since-at", self.last_stderr)
        self.assertIn("not allowed with", self.last_stderr)

    def test_malformed_since_at_is_refused_by_name_with_rc_2(self):
        for bad in ("not-a-date", "2026-13-02T00:00:00Z", "yesterday", ""):
            with self.subTest(bad=bad):
                code = self._exit_code(["--since-at", bad])
                self.assertEqual(code, 2)
                self.assertIn("invalid --since-at", self.last_stderr)

    def test_upper_bound_not_after_the_lower_one_is_refused_by_name(self):
        # EQUAL bounds included: refused rather than reported. An empty
        # report is indistinguishable from a corpus with no records, and
        # a moving `--since` lower bound can climb above a fixed --until
        # between two runs of the very same command.
        cases = (
            (["--since-at", "2026-09-02T12:55:05.807Z"], "2026-09-02T12:55:05.807Z"),
            (["--since-at", "2026-09-03T00:00:00Z"], "2026-09-02T00:00:00Z"),
            (["--since", "24h"], "2020-01-01T00:00:00Z"),
        )
        for lower, upper in cases:
            with self.subTest(lower=lower[0], upper=upper):
                code = self._exit_code(lower + ["--until", upper])
                self.assertEqual(code, 2)
                self.assertIn(
                    "does not follow the window's LOWER bound", self.last_stderr
                )

    def test_human_report_names_the_absolute_lower_bound(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cct.main(
                [
                    "--project-dir",
                    str(self.corpus),
                    "--pricing",
                    str(self.pricing_file),
                    "--since-at",
                    "2026-09-02T12:55:05.807Z",
                ]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("2026-09-02T12:55:05.807Z", out)
        # the unused relative default must NOT be advertised as the window
        self.assertNotIn("janela: 30d", out)


class WindowSubtractionLimitTests(TestEnvContext):
    """What the closed window does NOT promise (rail r2, S344).

    Two facts the doc and the --help now DECLARE, frozen here so a
    later edit cannot quietly change them: the default upper bound is
    ABSENT (not `now`), and both bounds are applied BEFORE dedup, so a
    group straddling a bound is truncated rather than carried whole.
    """

    BOUND = datetime(2026, 9, 2, 12, 55, 5, 807000, tzinfo=timezone.utc)
    AFTER = datetime(2026, 9, 2, 13, 0, 0, tzinfo=timezone.utc)
    FUTURE = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "limit-corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        self.pricing_file = self.project_dir / "pricing.yaml"
        self.pricing_file.write_text(
            "models:\n"
            "  claude-haiku-4-5:\n"
            "    input_per_mtok: 1.00\n"
            "    output_per_mtok: 5.00\n",
            encoding="utf-8",
        )

    def _write(self, rows):
        (self.corpus / "lim-sess.jsonl").write_text(
            "\n".join(
                _assistant_line(
                    msg_id=mid,
                    model="claude-haiku-4-5",
                    ts=ts,
                    usage=_usage(input_tokens=0, output_tokens=outp),
                    session_id="lim-sess",
                )
                for mid, ts, outp in rows
            )
            + "\n",
            encoding="utf-8",
        )

    def _json(self, extra):
        buf = io.StringIO()
        argv = [
            "--project-dir",
            str(self.corpus),
            "--pricing",
            str(self.pricing_file),
            "--json",
            "--since",
            "36500d",
        ] + extra
        with redirect_stdout(buf):
            rc = cct.main(argv)
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_default_upper_bound_is_absent_not_now(self):
        # A future-dated record (clock skew) is KEPT when --until is
        # omitted. If the default silently became `now`, this record
        # would vanish from the report without a word.
        self._write([("m_now", self.AFTER, 10), ("m_future", self.FUTURE, 20)])
        payload = self._json([])
        self.assertIsNone(payload["until"])
        self.assertEqual(payload["grand_total"]["turns"], 2)
        self.assertEqual(payload["grand_total"]["output_tokens"], 30)

    def test_until_help_does_not_promise_a_default_it_never_applies(self):
        parser = cct.build_parser()
        helps = [
            a.help
            for a in parser._actions
            if "--until" in getattr(a, "option_strings", [])
        ]
        self.assertEqual(len(helps), 1)
        self.assertNotIn("Default: now", helps[0])
        self.assertIn("unbounded above", helps[0])

    def test_a_group_straddling_the_bound_is_TRUNCATED_not_carried(self):
        # One message, two progressive snapshots either side of the
        # bound. Both bounds filter BEFORE dedup, so the bounded run
        # sees only the first snapshot -- which is why subtracting two
        # runs is not identical to one closed-window rollup, the limit
        # docs/cost-of-operation.md declares by name.
        self._write([("m_split", self.BOUND, 100), ("m_split", self.AFTER, 900)])
        whole = self._json([])
        self.assertEqual(whole["grand_total"]["turns"], 1)
        self.assertEqual(whole["grand_total"]["output_tokens"], 900)
        bounded = self._json(["--until", "2026-09-02T12:55:05.807Z"])
        self.assertEqual(bounded["grand_total"]["turns"], 1)
        self.assertEqual(bounded["grand_total"]["output_tokens"], 100)
        # The subtraction of the two runs reports ZERO turns and 800
        # output tokens -- neither what a closed rollup would say.
        self.assertEqual(
            whole["grand_total"]["turns"] - bounded["grand_total"]["turns"], 0
        )


if __name__ == "__main__":
    unittest.main()
