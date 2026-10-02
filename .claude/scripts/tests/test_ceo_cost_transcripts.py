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


# ---------------------------------------------------------------------------
# Routing invariant (PLAN-186 AC-13, S361)
# ---------------------------------------------------------------------------
#
# Every fixture below is SYNTHETIC: sidecars and transcripts are written
# under TestEnvContext's tmp dir in the exact on-disk shape the harness
# uses (``<session>/subagents[/workflows/<run>]/agent-<id>.meta.json`` next
# to ``agent-<id>.jsonl``). No test reads the real corpus and nothing
# touches the network. The VETO floor is a SYNTHETIC set unless a test says
# otherwise, so a legitimate edit of the live allowlist (the W1 land adds
# ``claude-fable-5-1``) cannot turn a test red.

_FLOOR_ROLES = frozenset({"code-reviewer", "security-engineer"})
_FLOOR_ALLOWED = frozenset({"claude-opus-5", "claude-fable-5"})


class _RoutingFixture(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.corpus = self.project_dir / "routing-corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        self.now = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
        patcher = mock.patch.object(
            cct, "_floor_source", return_value=(_FLOOR_ROLES, _FLOOR_ALLOWED)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def spawn(
        self,
        agent_id,
        side,
        served,
        *,
        workflow=None,
        session="sess-1",
        raw_lines=None,
    ):
        """Write one spawn: its sidecar and a transcript whose assistant
        turns carry `served` = [(model, ts)] (``None`` writes no
        transcript at all). Returns the directory holding both files."""
        base = self.corpus / session / "subagents"
        if workflow:
            base = base / "workflows" / workflow
        base.mkdir(parents=True, exist_ok=True)
        (base / ("agent-%s.meta.json" % agent_id)).write_text(
            json.dumps(side), encoding="utf-8"
        )
        if served is None:
            return base
        lines = [
            _assistant_line(
                msg_id="msg_%s_%d" % (agent_id, i),
                model=model,
                ts=ts,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id=session,
            )
            for i, (model, ts) in enumerate(served)
        ]
        lines.extend(raw_lines or [])
        (base / ("agent-%s.jsonl" % agent_id)).write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        return base

    def turns(self, model, n=1):
        return [(model, self.now + timedelta(seconds=i)) for i in range(n)]

    def run_routing(self, **kw):
        return cct.routing_invariant(self.corpus, **kw)


class RoutingModelFamilyAndDeclarationTests(TestEnvContext):
    def test_model_family_parses_every_id_shape_the_fleet_uses(self):
        for model_id, fam in (
            ("claude-opus-5-5", "opus"),
            ("claude-opus-4-8", "opus"),
            ("claude-sonnet-5", "sonnet"),
            ("claude-fable-5-1", "fable"),
            ("claude-haiku-4-5-20251001", "haiku"),
            ("claude-3-5-haiku-20241022", "haiku"),
            ("  Claude-Sonnet-5-5  ", "sonnet"),
        ):
            self.assertEqual(cct.model_family(model_id), fam, model_id)
        for bad in (None, 7, "", "gpt-5", "sonnet", "<synthetic>"):
            self.assertIsNone(cct.model_family(bad), repr(bad))

    def test_families_are_derived_from_the_fleet_tables_not_retyped(self):
        expected = {cct.model_family(m) for m in cct._EMBEDDED_PRICING}
        expected.discard(None)
        # Without a floor the vocabulary is exactly the pricing table's.
        self.assertEqual(cct.known_families(), frozenset(expected))
        # A family only the floor names still counts ...
        floor = (frozenset({"r"}), frozenset({"claude-zeta-1"}))
        self.assertIn("zeta", cct.known_families(floor))
        # ... and the four families the harness aliases today are all there.
        self.assertTrue({"opus", "sonnet", "haiku", "fable"} <= cct.known_families())

    def test_classify_declared_table(self):
        fams = cct.known_families()
        cases = (
            (None, ("none", "")),
            ("", ("none", "")),
            ("inherit", ("none", "inherit")),
            ("  INHERIT ", ("none", "inherit")),
            ("sonnet", ("alias", "sonnet")),
            ("Opus", ("alias", "opus")),
            ("sonnet[1m]", ("alias", "sonnet")),
            ("claude-fable-5-1[1m]", ("id", "claude-fable-5-1")),
            ("claude-opus-5", ("id", "claude-opus-5")),
            ("opusplan", ("unclassified", "opusplan")),
            ("mythos", ("unclassified", "mythos")),
            (5, ("unclassified", "5")),
            (["opus"], ("unclassified", "['opus']")),
        )
        for raw, want in cases:
            self.assertEqual(cct.classify_declared(raw, fams), want, repr(raw))

    def test_declaration_matches_alias_by_family_and_id_exactly(self):
        m = cct.declaration_matches
        self.assertTrue(m("alias", "sonnet", "claude-sonnet-5"))
        self.assertTrue(m("alias", "sonnet", "claude-sonnet-5-5"))
        self.assertFalse(m("alias", "sonnet", "claude-opus-5-5"))
        self.assertTrue(m("id", "claude-opus-5", "claude-opus-5"))
        # an exact id is exact: the next generation is NOT the same id ...
        self.assertFalse(m("id", "claude-opus-5", "claude-opus-5-5"))
        # ... but a dated build of the SAME id is.
        self.assertTrue(m("id", "claude-haiku-4-5", "claude-haiku-4-5-20251001"))
        self.assertFalse(m("id", "claude-haiku-4-5", "claude-haiku-4-5-2025"))
        self.assertFalse(m("none", "", "claude-opus-5"))


class RoutingInvariantControlsTests(_RoutingFixture):
    """K-A1: the positive/negative control pair. If the RED case here ever
    stops biting, the detector is dead (module docstring, K-A1)."""

    def test_positive_control_declared_sonnet_served_opus_is_RED(self):
        self.spawn(
            "a1",
            {"agentType": "workflow-subagent", "description": "site:one", "model": "sonnet"},
            self.turns("claude-opus-5-5", 3),
            workflow="wf_1",
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual(len(r["violations"]), 1)
        v = r["violations"][0]
        self.assertEqual(v["kinds"], ["MISMATCH"])
        self.assertEqual(v["declared"], "sonnet")
        self.assertEqual(v["served"], {"claude-opus-5-5": 3})
        self.assertEqual(v["label"], "site:one")
        self.assertEqual(v["rail"], "workflow")

    def test_negative_control_declared_equals_served_is_GREEN(self):
        self.spawn(
            "a1",
            {"agentType": "workflow-subagent", "description": "site:one", "model": "sonnet"},
            self.turns("claude-sonnet-5-5", 3),
            workflow="wf_1",
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["counts"]["declared_compared"], 1)
        self.assertEqual(r["counts"]["compared_spawns"], 1)
        self.assertIn("1 spawn(s) compared: 1 declared", r["reason"])

    def test_the_two_controls_in_one_corpus_flip_the_verdict_exactly_once(self):
        good = {"agentType": "general-purpose", "description": "good", "model": "haiku"}
        self.spawn("g1", good, self.turns("claude-haiku-4-5-20251001"))
        self.assertEqual(self.run_routing()["verdict"], "GREEN")
        self.spawn(
            "b1",
            {"agentType": "general-purpose", "description": "bad", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual([v["label"] for v in r["violations"]], ["bad"])

    def test_s361_datum_alias_is_matched_by_family_never_by_a_pinned_id(self):
        # The measured fact that killed the pinned alias->id table: on one
        # harness the SAME alias was served by two different ids.
        for i, served in enumerate(("claude-sonnet-5", "claude-sonnet-5-5")):
            self.spawn(
                "s%d" % i,
                {"agentType": "general-purpose", "description": "d%d" % i, "model": "sonnet"},
                self.turns(served),
            )
        # and a spawn that declares nothing is served by the seat's model:
        self.spawn(
            "u1",
            {"agentType": "general-purpose", "description": "undeclared"},
            self.turns("claude-opus-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(
            r["alias_resolutions"],
            {"sonnet": {"claude-sonnet-5": 1, "claude-sonnet-5-5": 1}},
        )
        self.assertEqual(r["counts"]["undeclared"], 1)
        self.assertEqual(r["counts"]["declared_compared"], 2)

    def test_exact_id_declarations_are_exact(self):
        self.spawn(
            "e1",
            {"agentType": "general-purpose", "description": "wrong-gen", "model": "claude-opus-5"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "e2",
            {"agentType": "general-purpose", "description": "dated", "model": "claude-haiku-4-5"},
            self.turns("claude-haiku-4-5-20251001"),
        )
        self.spawn(
            "e3",
            {"agentType": "general-purpose", "description": "suffix", "model": "claude-fable-5-1[1m]"},
            self.turns("claude-fable-5-1"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual([v["label"] for v in r["violations"]], ["wrong-gen"])

    def test_a_partly_served_spawn_is_MIXED_and_carries_the_turn_counts(self):
        self.spawn(
            "m1",
            {"agentType": "general-purpose", "description": "fell-back", "model": "claude-fable-5"},
            self.turns("claude-fable-5", 5) + self.turns("claude-opus-4-8", 2),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        v = r["violations"][0]
        self.assertEqual(v["kinds"], ["MIXED"])
        self.assertEqual(v["served"], {"claude-fable-5": 5, "claude-opus-4-8": 2})

    def test_streamed_chunks_of_one_message_resolve_to_the_terminal_model(self):
        # The cost report's own rule (dedup keeps the terminal chunk): a
        # harness that stamps the FIRST streamed chunk with another model
        # must not fabricate a MIXED verdict here either.
        base = self.spawn(
            "c1",
            {"agentType": "general-purpose", "description": "chunks", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        chunks = [
            _assistant_line(
                msg_id="msg_chunked",
                model=model,
                ts=self.now + timedelta(seconds=10 + i),
                usage=_usage(input_tokens=1, output_tokens=out),
                session_id="sess-1",
            )
            for i, (model, out) in enumerate(
                (("claude-opus-5-5", 1), ("claude-sonnet-5-5", 50))
            )
        ]
        with (base / "agent-c1.jsonl").open("a", encoding="utf-8") as f:
            f.write("\n".join(chunks) + "\n")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])

    def test_the_verdict_travels_with_the_report_pipeline(self):
        self.spawn(
            "a1",
            {"agentType": "general-purpose", "description": "bad", "model": "sonnet"},
            [("claude-opus-5-5", datetime.now(timezone.utc) - timedelta(hours=1))],
        )
        rolled = cct.transcript_rollup(self.corpus, cutoff=None, by="model")
        self.assertEqual(rolled["routing"]["verdict"], "RED")
        collected = cct.collect(root_arg=str(self.corpus), cutoff=None, by="model")
        self.assertEqual(collected["routing"]["verdict"], "RED")
        block = "\n".join(cct.render_block(collected))
        self.assertIn("ROUTING INVARIANT (PLAN-186 AC-13): RED", block)
        self.assertIn("VIOLATION [MISMATCH]", block)


class RoutingFloorPredicateTests(_RoutingFixture):
    def test_declared_equals_served_is_silent_about_the_floor(self):
        # The AC-10 hole: a VETO archetype declared `sonnet` and served
        # Sonnet MATCHES ITSELF -- only the second predicate sees it.
        self.spawn(
            "v1",
            {"agentType": "code-reviewer", "description": "probe", "model": "sonnet"},
            self.turns("claude-sonnet-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual(r["violations"][0]["kinds"], ["FLOOR_BREACH"])
        self.assertEqual(r["counts"]["declared_compared"], 1)
        self.assertEqual(r["counts"]["floor_checked"], 1)
        # one spawn fed both predicates: it is ONE compared spawn, not two
        self.assertEqual(r["counts"]["compared_spawns"], 1)
        self.assertIn("of 1 compared", r["reason"])

    def test_floor_is_membership_never_a_family_prefix(self):
        # `claude-opus-5-5` shares the family of the allowed `claude-opus-5`
        # and is still NOT a member of this (synthetic) floor.
        self.spawn(
            "v1",
            {"agentType": "code-reviewer", "description": "outside"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "v2",
            {"agentType": "code-reviewer", "description": "inside"},
            self.turns("claude-opus-5"),
        )
        r = self.run_routing()
        self.assertEqual([v["label"] for v in r["violations"]], ["outside"])
        self.assertEqual(r["violations"][0]["kinds"], ["FLOOR_BREACH"])

    def test_an_undeclared_veto_spawn_is_still_floor_checked(self):
        self.spawn(
            "v1",
            {"agentType": "security-engineer", "description": "pin-less"},
            self.turns("claude-sonnet-4-6"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual(r["counts"]["declared_compared"], 0)
        self.assertEqual(r["counts"]["floor_checked"], 1)

    def test_archetype_comes_from_custom_agent_type_first(self):
        # An in-process teammate: agentType is its NAME, the archetype is
        # in customAgentType.
        self.spawn(
            "t1",
            {
                "agentType": "ver-part6",
                "customAgentType": "security-engineer",
                "description": "teammate",
                "model": "haiku",
                "taskKind": "in_process_teammate",
            },
            self.turns("claude-haiku-4-5-20251001"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        v = r["violations"][0]
        self.assertEqual(v["kinds"], ["FLOOR_BREACH"])
        self.assertEqual(v["archetype"], "security-engineer")
        self.assertEqual(v["rail"], "native")

    def test_a_non_veto_spawn_below_the_floor_is_fine(self):
        self.spawn(
            "n1",
            {"agentType": "general-purpose", "description": "builder", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN")
        self.assertEqual(r["counts"]["floor_checked"], 0)

    def test_floor_source_unreadable_is_INCONCLUSIVE_never_a_silent_skip(self):
        self.spawn(
            "n1",
            {"agentType": "general-purpose", "description": "ok", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        with mock.patch.object(cct, "_floor_source", return_value=None):
            r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("floor source unreadable", r["reason"])
        self.assertIsNone(r["floor"])


class RoutingRealFloorSourceTests(TestEnvContext):
    """The one place the REAL floor accessor runs (no fixture patch)."""

    def test_floor_is_imported_from_the_signed_source_not_retyped(self):
        from _lib import agent_frontmatter as af

        real = cct._floor_source()
        self.assertIsNotNone(real)
        roles, allowed = real
        self.assertEqual(roles, frozenset(af.VETO_FLOOR_ROLES))
        self.assertEqual(allowed, frozenset(m.lower() for m in af.VETO_FLOOR_ALLOWED))
        self.assertTrue(roles and allowed)
        # the detector covers ALL the floor roles, not a remembered subset
        self.assertGreaterEqual(len(roles), 5)

    def test_the_live_floor_admits_a_member_and_refuses_a_non_member(self):
        # Dynamic, so editing the allowlist never turns this red: the
        # member is whatever the signed source says, the non-member is a
        # Haiku id the floor can never admit.
        roles, allowed = cct._floor_source()
        role = sorted(roles)[0]
        member = sorted(allowed)[0]
        corpus = self.project_dir / "live-floor"
        base = corpus / "s" / "subagents"
        base.mkdir(parents=True)
        now = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)

        def write(agent_id, served):
            (base / ("agent-%s.meta.json" % agent_id)).write_text(
                json.dumps({"agentType": role, "description": agent_id}), encoding="utf-8"
            )
            (base / ("agent-%s.jsonl" % agent_id)).write_text(
                _assistant_line(
                    msg_id="m_" + agent_id,
                    model=served,
                    ts=now,
                    usage=_usage(input_tokens=1, output_tokens=1),
                    session_id="s",
                )
                + "\n",
                encoding="utf-8",
            )

        write("ok", member)
        self.assertEqual(cct.routing_invariant(corpus)["verdict"], "GREEN")
        write("bad", "claude-haiku-4-5-20251001")
        r = cct.routing_invariant(corpus)
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual([v["label"] for v in r["violations"]], ["bad"])


class RoutingVerdictStatesTests(_RoutingFixture):
    """GREEN is earned: nothing-to-compare is VACUOUS and anything the
    check could not read or classify is INCONCLUSIVE -- never a pass."""

    def test_an_empty_corpus_is_VACUOUS_not_GREEN(self):
        r = self.run_routing()
        self.assertEqual(r["verdict"], "VACUOUS")
        self.assertEqual(r["counts"]["sidecars"], 0)

    def test_only_undeclared_spawns_is_VACUOUS(self):
        self.spawn(
            "u1",
            {"agentType": "general-purpose", "description": "none"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "u2",
            {"agentType": "general-purpose", "description": "inh", "model": "inherit"},
            self.turns("claude-opus-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "VACUOUS")
        self.assertEqual(r["counts"]["undeclared"], 2)
        self.assertEqual(r["counts"]["declared"], 0)

    def test_a_declared_spawn_that_was_never_served_is_VACUOUS(self):
        # no transcript at all, and a transcript with only <synthetic>
        # turns (a quota wall): nothing was SERVED, so nothing is compared.
        self.spawn("n1", {"agentType": "general-purpose", "description": "x", "model": "sonnet"}, None)
        self.spawn(
            "n2",
            {"agentType": "general-purpose", "description": "y", "model": "sonnet"},
            self.turns("<synthetic>", 2),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "VACUOUS")
        self.assertEqual(r["counts"]["declared"], 2)
        self.assertEqual(r["counts"]["no_served"], 2)
        self.assertEqual(r["counts"]["synthetic_turns_ignored"], 2)

    def test_synthetic_turns_never_make_a_match_a_violation(self):
        self.spawn(
            "s1",
            {"agentType": "general-purpose", "description": "x", "model": "sonnet"},
            self.turns("claude-sonnet-5-5", 2) + self.turns("<synthetic>", 3),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])

    def test_unclassified_declarations_are_INCONCLUSIVE_never_GREEN(self):
        self.spawn(
            "ok",
            {"agentType": "general-purpose", "description": "ok", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        self.spawn(
            "u1",
            {"agentType": "general-purpose", "description": "plan", "model": "opusplan"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "u2",
            {"agentType": "general-purpose", "description": "num", "model": 5},
            self.turns("claude-opus-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["counts"]["unclassified"], 2)
        self.assertEqual(sorted(r["unclassified_samples"]), ["5", "opusplan"])
        self.assertIn("unclassified declaration", r["reason"])

    def test_RED_outranks_INCONCLUSIVE(self):
        self.spawn(
            "bad",
            {"agentType": "general-purpose", "description": "bad", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "odd",
            {"agentType": "general-purpose", "description": "odd", "model": "opusplan"},
            self.turns("claude-opus-5-5"),
        )
        self.assertEqual(self.run_routing()["verdict"], "RED")

    def test_a_torn_assistant_line_makes_the_verdict_INCONCLUSIVE(self):
        self.spawn(
            "t1",
            {"agentType": "general-purpose", "description": "torn", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
            raw_lines=['{"type": "assistant", "message": {"usage": '],
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertGreaterEqual(r["counts"]["incomplete_reads"], 1)

    def test_an_assistant_turn_without_a_model_id_is_INCONCLUSIVE(self):
        base = self.spawn(
            "m1",
            {"agentType": "general-purpose", "description": "nomodel", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        rec = json.loads(
            _assistant_line(
                msg_id="msg_nomodel",
                model="x",
                ts=self.now + timedelta(seconds=30),
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="sess-1",
            )
        )
        del rec["message"]["model"]
        with (base / "agent-m1.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["counts"]["served_unresolved"], 1)

    def test_unreadable_and_oversized_sidecars_are_INCONCLUSIVE(self):
        base = self.spawn(
            "ok",
            {"agentType": "general-purpose", "description": "ok", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        (base / "agent-bad.meta.json").write_text("{not json", encoding="utf-8")
        (base / "agent-list.meta.json").write_text("[1, 2]", encoding="utf-8")
        (base / "agent-big.meta.json").write_text(
            json.dumps({"model": "sonnet", "pad": "x" * (cct._SIDECAR_MAX_BYTES + 10)}),
            encoding="utf-8",
        )
        # an unreadable sidecar gates the verdict only when its spawn has
        # turns in the window: give each one the transcript of a live spawn
        live = (base / "agent-ok.jsonl").read_text(encoding="utf-8")
        for name in ("bad", "list", "big"):
            (base / ("agent-%s.jsonl" % name)).write_text(live, encoding="utf-8")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["counts"]["unreadable_sidecars"], 3)

    def test_a_symlinked_transcript_is_refused_not_followed(self):
        outside = self.project_dir / "outside.jsonl"
        outside.write_text(
            _assistant_line(
                msg_id="m_out",
                model="claude-opus-5-5",
                ts=self.now,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="sess-1",
            )
            + "\n",
            encoding="utf-8",
        )
        base = self.spawn(
            "l1",
            {"agentType": "general-purpose", "description": "linked", "model": "sonnet"},
            None,
        )
        try:
            (base / "agent-l1.jsonl").symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - no symlinks
            self.skipTest("symlinks unavailable on this platform")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["counts"]["refused_paths"], 1)
        self.assertEqual(r["violations"], [])

    def test_an_internal_failure_is_INCONCLUSIVE_never_GREEN_and_never_raises(self):
        with mock.patch.object(cct, "routing_invariant", side_effect=RuntimeError("boom")):
            r = cct.routing_invariant_safe(self.corpus)
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("RuntimeError", r["reason"])
        self.assertEqual(cct.routing_rc(r), cct.ROUTING_RC_NOT_PROVEN)


class RoutingWindowAndLabelTests(_RoutingFixture):
    def test_the_window_filters_TURNS_with_the_cost_reports_own_bounds(self):
        old = self.now - timedelta(days=40)
        self.spawn(
            "w1",
            {"agentType": "general-purpose", "description": "old-bad", "model": "haiku"},
            [("claude-opus-5-5", old)],
        )
        self.spawn(
            "w2",
            {"agentType": "general-purpose", "description": "new-good", "model": "haiku"},
            self.turns("claude-haiku-4-5-20251001"),
        )
        wide = self.run_routing()
        self.assertEqual(wide["verdict"], "RED")
        windowed = self.run_routing(cutoff=self.now - timedelta(days=30))
        self.assertEqual(windowed["verdict"], "GREEN", windowed["reason"])
        self.assertEqual(windowed["counts"]["out_of_window"], 1)
        closed = self.run_routing(cutoff=old - timedelta(days=1), until=old + timedelta(days=1))
        self.assertEqual(closed["verdict"], "RED")
        self.assertEqual(closed["counts"]["out_of_window"], 1)

    def test_label_is_the_sidecar_description_then_name_then_the_agent_id(self):
        self.spawn(
            "d1",
            {"agentType": "workflow-subagent", "description": "  site:  a\nb ", "model": "haiku"},
            self.turns("claude-opus-5-5"),
            workflow="wf_9",
        )
        self.spawn(
            "d2",
            {"agentType": "general-purpose", "name": "named-mate", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "d3",
            {"agentType": "workflow-subagent", "model": "haiku"},
            self.turns("claude-opus-5-5"),
            workflow="wf_9",
        )
        r = self.run_routing()
        labels = sorted(v["label"] for v in r["violations"])
        self.assertEqual(labels, ["agent-d3", "named-mate", "site: a b"])

    def test_rail_follows_the_path_workflows_are_not_native(self):
        self.spawn(
            "r1",
            {"agentType": "workflow-subagent", "description": "wf", "model": "haiku"},
            self.turns("claude-opus-5-5"),
            workflow="wf_1",
        )
        self.spawn(
            "r2",
            {"agentType": "general-purpose", "description": "nat", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        rails = {v["label"]: v["rail"] for v in self.run_routing()["violations"]}
        self.assertEqual(rails, {"wf": "workflow", "nat": "native"})

    def test_the_detector_writes_nothing(self):
        self.spawn(
            "x1",
            {"agentType": "code-reviewer", "description": "bad", "model": "haiku"},
            self.turns("claude-haiku-4-5-20251001"),
        )

        def snapshot():
            return {
                str(p.relative_to(self.project_dir)): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in sorted(self.project_dir.rglob("*"))
            }

        before = snapshot()
        self.run_routing()
        cct.transcript_rollup(self.corpus, cutoff=None, by="model")
        self.assertEqual(snapshot(), before)


class RoutingCliTests(_RoutingFixture):
    """The verdict is evaluated and PRINTED on every run; only
    `--assert-routing` turns it into the exit code."""

    def _main(self, extra):
        buf = io.StringIO()
        argv = ["--project-dir", str(self.corpus), "--since", "36500d"] + extra
        with redirect_stdout(buf):
            rc = cct.main(argv)
        return rc, buf.getvalue()

    def _red(self):
        self.spawn(
            "r1",
            {"agentType": "general-purpose", "description": "bad", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )

    def _green(self):
        self.spawn(
            "g1",
            {"agentType": "general-purpose", "description": "good", "model": "haiku"},
            self.turns("claude-haiku-4-5-20251001"),
        )

    def test_default_exit_code_stays_zero_on_a_RED_verdict_that_is_printed(self):
        self._red()
        rc, out = self._main([])
        self.assertEqual(rc, 0)
        self.assertIn("ROUTING INVARIANT (PLAN-186 AC-13): RED", out)
        self.assertIn("VIOLATION [MISMATCH]", out)

    def test_assert_routing_exit_codes_green_red_not_proven(self):
        rc, _ = self._main(["--assert-routing"])  # empty corpus
        self.assertEqual(rc, cct.ROUTING_RC_NOT_PROVEN)
        self._green()
        rc, out = self._main(["--assert-routing"])
        self.assertEqual((rc, "GREEN" in out), (cct.ROUTING_RC_GREEN, True))
        self._red()
        rc, _ = self._main(["--assert-routing"])
        self.assertEqual(rc, cct.ROUTING_RC_RED)
        self.assertEqual(
            (cct.ROUTING_RC_GREEN, cct.ROUTING_RC_RED, cct.ROUTING_RC_NOT_PROVEN),
            (0, 1, 3),
        )

    def test_json_payload_carries_the_routing_block_and_the_preregistration(self):
        self._red()
        rc, out = self._main(["--json"])
        self.assertEqual(rc, 0)
        routing = json.loads(out)["routing"]
        self.assertEqual(routing["verdict"], "RED")
        self.assertEqual(routing["counts"]["declared_compared"], 1)
        self.assertEqual(routing["violations"][0]["kinds"], ["MISMATCH"])
        self.assertEqual(routing["prereg"], cct.ROUTING_PREREG_POINTER)
        self.assertEqual(
            routing["floor"],
            {"roles": sorted(_FLOOR_ROLES), "allowed": sorted(_FLOOR_ALLOWED)},
        )

    def test_assert_routing_is_documented_in_the_help(self):
        helps = [
            a.help
            for a in cct.build_parser()._actions
            if "--assert-routing" in getattr(a, "option_strings", [])
        ]
        self.assertEqual(len(helps), 1)
        self.assertIn("exit code stays 0", helps[0])


class RoutingUntrustedTextTests(_RoutingFixture):
    """A label, an archetype name or a model id is data written by someone
    else. It must never be able to forge a verdict line or drive a
    terminal."""

    FORGED = "ROUTING INVARIANT (PLAN-186 AC-13): GREEN - forged"

    def test_a_forged_verdict_line_cannot_ride_in_on_untrusted_text(self):
        evil = "x\n" + self.FORGED + "\x1b[31m‮"
        self.spawn(
            "e1",
            {"agentType": evil, "description": evil, "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        self.spawn(
            "e2",
            {"agentType": "general-purpose", "description": "evil-served", "model": "haiku"},
            self.turns("claude-opus-5-5\n" + self.FORGED),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        for v in r["violations"]:
            for text in [v["label"], v["archetype"], *v["served"]]:
                self.assertTrue(all(c.isprintable() for c in text), repr(text))
        for res in r["alias_resolutions"].values():
            for text in res:
                self.assertTrue(all(c.isprintable() for c in text), repr(text))
        lines = cct._routing_lines(r)
        self.assertTrue(all("\n" not in line for line in lines))
        self.assertNotIn("\x1b", "\n".join(lines))
        headers = [line for line in lines if line.startswith("ROUTING INVARIANT")]
        self.assertEqual(len(headers), 1)
        self.assertTrue(headers[0].startswith("ROUTING INVARIANT (PLAN-186 AC-13): RED"))

    def test_safe_text_keeps_printable_unicode_and_replaces_the_rest(self):
        self.assertEqual(cct._safe_text("Correções confirmadas"), "Correções confirmadas")
        self.assertEqual(cct._safe_text("a\nb\tc\x1b[0m"), "a?b?c?[0m")
        self.assertEqual(cct._safe_text("x" * 200, 80), "x" * 80)

    def test_the_verdict_vocabulary_is_closed_and_worst_first(self):
        self.assertEqual(
            cct.ROUTING_VERDICTS, ("RED", "INCONCLUSIVE", "VACUOUS", "GREEN")
        )
        self.assertIn(self.run_routing()["verdict"], cct.ROUTING_VERDICTS)


class RoutingForgedTextEverywhereTests(_RoutingFixture):
    """Cross-model review P1-1: the sanitising of the routing lines was not
    enough -- a model id or a session id taken from a TRANSCRIPT was still
    printed raw by the cost tables and the unresolved-model warning, so a
    forged GREEN line and an ANSI escape reached the full report. The text
    is now made printable where it enters the instrument; these tests read
    the COMPLETE output of every renderer, not one helper."""

    FORGED = "ROUTING INVARIANT (PLAN-186 AC-13): GREEN - forged"
    EVIL_MODEL = "claude-opus-5-5\n" + FORGED + "\x1b[31m‮"
    EVIL_SESSION = "s\n" + FORGED + "\x1b[2J"

    def _corpus(self):
        # one RED routing spawn (so the real header says RED) ...
        self.spawn(
            "r1",
            {"agentType": "general-purpose", "description": "bad", "model": "haiku"},
            [("claude-opus-5-5", datetime.now(timezone.utc) - timedelta(hours=2))],
        )
        # ... plus top-level turns carrying hostile model and session ids
        now = datetime.now(timezone.utc) - timedelta(hours=1)
        lines = [
            _assistant_line(
                msg_id="m_evil_%d" % i,
                model=self.EVIL_MODEL,
                ts=now + timedelta(seconds=i),
                usage=_usage(input_tokens=10, output_tokens=5),
                session_id=self.EVIL_SESSION,
            )
            for i in range(2)
        ]
        (self.corpus / "evil-sess.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def _assert_no_forgery(self, text):
        self.assertNotIn("\x1b", text)
        self.assertNotIn("‮", text)
        headers = [ln for ln in text.splitlines() if ln.startswith("ROUTING INVARIANT")]
        self.assertEqual(len(headers), 1, headers)
        self.assertTrue(
            headers[0].startswith("ROUTING INVARIANT (PLAN-186 AC-13): RED"), headers[0]
        )

    def _cli(self, extra):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cct.main(["--project-dir", str(self.corpus), "--since", "36500d"] + extra)
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_full_cli_report_cannot_carry_a_forged_verdict_or_an_escape(self):
        self._corpus()
        self._assert_no_forgery(self._cli([]))
        self._assert_no_forgery(self._cli(["--by", "session"]))
        self._assert_no_forgery(self._cli(["--by", "role,model"]))

    def test_json_report_keys_are_printable_too(self):
        self._corpus()
        payload = json.loads(self._cli(["--json", "--by", "session"]))
        keys = list(payload["by_session"]) + list(payload["unresolved_models"])
        self.assertTrue(keys)
        for key in keys:
            self.assertTrue(all(c.isprintable() for c in key), repr(key))
        model_keys = json.loads(self._cli(["--json"]))["by_model"]
        for key in model_keys:
            self.assertTrue(all(c.isprintable() for c in key), repr(key))

    def test_the_block_the_two_callers_render_cannot_forge_either(self):
        self._corpus()
        collected = cct.collect(root_arg=str(self.corpus), cutoff=None, by="model")
        self._assert_no_forgery("\n".join(cct.render_block(collected)))
        collected = cct.collect(root_arg=str(self.corpus), cutoff=None, by="session")
        self._assert_no_forgery("\n".join(cct.render_block(collected)))

    def test_every_string_a_record_carries_is_printable(self):
        obj = json.loads(
            _assistant_line(
                msg_id="m1",
                model=self.EVIL_MODEL,
                ts=self.now,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id=self.EVIL_SESSION,
                effort="high\n" + self.FORGED,
            )
        )
        rec = cct._extract_record(obj, "subagent", "fallback\nx", cct.ScanCounters())
        self.assertIsNotNone(rec)
        for text in (rec.model, rec.session_id, rec.effort):
            self.assertTrue(all(c.isprintable() for c in text), repr(text))
        # a clean id passes through untouched: no benign model is rewritten
        clean = json.loads(
            _assistant_line(
                msg_id="m2",
                model="claude-opus-5-5[1m]",
                ts=self.now,
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="0000aaaa-1111",
            )
        )
        rec = cct._extract_record(clean, "subagent", "f", cct.ScanCounters())
        self.assertEqual((rec.model, rec.session_id), ("claude-opus-5-5", "0000aaaa-1111"))


class RoutingReadsEveryTurnTests(_RoutingFixture):
    """Cross-model review P1-2: the cost reader drops an assistant turn whose
    ``usage`` is null, absent or empty. The served model is a fact of the
    turn, not of its bill, so the routing reader must not lose it."""

    def _spawn_with_tail(self, agent_id, tail_record):
        base = self.spawn(
            agent_id,
            {"agentType": "general-purpose", "description": agent_id, "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        with (base / ("agent-%s.jsonl" % agent_id)).open("a", encoding="utf-8") as f:
            f.write(json.dumps(tail_record) + "\n")
        return base

    def _opus_turn(self, mutate):
        rec = json.loads(
            _assistant_line(
                msg_id="msg_divergent",
                model="claude-opus-5-5",
                ts=self.now + timedelta(seconds=30),
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="sess-1",
            )
        )
        mutate(rec)
        return rec

    def test_a_divergent_turn_with_null_usage_is_RED_not_GREEN(self):
        self._spawn_with_tail(
            "n1", self._opus_turn(lambda r: r["message"].__setitem__("usage", None))
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED", r["reason"])
        v = r["violations"][0]
        self.assertEqual(v["kinds"], ["MIXED"])
        self.assertEqual(v["served"], {"claude-opus-5-5": 1, "claude-sonnet-5-5": 1})
        self.assertEqual(cct.routing_rc(r), cct.ROUTING_RC_RED)

    def test_absent_and_empty_usage_are_read_too(self):
        self._spawn_with_tail(
            "n2", self._opus_turn(lambda r: r["message"].pop("usage"))
        )
        self._spawn_with_tail(
            "n3", self._opus_turn(lambda r: r["message"].__setitem__("usage", {}))
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED", r["reason"])
        self.assertEqual(sorted(v["label"] for v in r["violations"]), ["n2", "n3"])

    def test_a_turn_with_no_message_object_cannot_be_read_and_says_so(self):
        self._spawn_with_tail(
            "n4",
            {"type": "assistant", "timestamp": "2026-10-02T12:00:30.000Z", "message": None},
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertGreaterEqual(r["counts"]["incomplete_reads"], 1)

    def test_the_cost_reader_is_unchanged_it_still_drops_that_turn(self):
        obj = self._opus_turn(lambda r: r["message"].__setitem__("usage", None))
        c = cct.ScanCounters()
        self.assertIsNone(cct._extract_record(obj, "subagent", "s", c))
        rec = cct._extract_record(obj, "subagent", "s", c, usage_optional=True)
        self.assertIsNotNone(rec)
        self.assertEqual((rec.input_tokens, rec.output_tokens), (0, 0))
        self.assertEqual(c.missing_usage_keys, 0)
        # and the CLI cost total over the same corpus does NOT count the
        # usage-less turn: only the one billed Sonnet turn
        self._spawn_with_tail("n5", obj)
        rolled = cct.transcript_rollup(self.corpus, cutoff=None, by="model")
        self.assertEqual(rolled["grand_total"]["turns"], 1)
        self.assertEqual(rolled["routing"]["verdict"], "RED")


class RoutingTerminalChunkTests(_RoutingFixture):
    """Cross-model review P2-1: on equal ``output_tokens`` the FIRST chunk
    used to win (``max`` keeps the first maximum), so file order decided the
    verdict by accident. The terminal chunk is the LATER one."""

    def _chunks(self, agent_id, first, second):
        base = self.spawn(
            agent_id,
            {"agentType": "general-purpose", "description": agent_id, "model": "sonnet"},
            None,
        )
        lines = [
            _assistant_line(
                msg_id="msg_tie_" + agent_id,
                model=model,
                ts=self.now + timedelta(seconds=i),
                usage=_usage(input_tokens=1, output_tokens=7),
                session_id="sess-1",
            )
            for i, model in enumerate((first, second))
        ]
        (base / ("agent-%s.jsonl" % agent_id)).write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def test_dedup_breaks_a_tie_by_the_later_chunk_in_both_orders(self):
        def rec(model, out):
            return cct.UsageRecord(
                key="mid:x", ts=self.now, model=model, effort=None, session_id="s",
                role="subagent", output_tokens=out,
            )

        a, _ = cct.dedup([rec("claude-opus-5-5", 7), rec("claude-sonnet-5-5", 7)])
        b, _ = cct.dedup([rec("claude-sonnet-5-5", 7), rec("claude-opus-5-5", 7)])
        self.assertEqual(a[0].model, "claude-sonnet-5-5")
        self.assertEqual(b[0].model, "claude-opus-5-5")
        # a strictly larger count still wins whatever its position
        c, _ = cct.dedup([rec("claude-opus-5-5", 9), rec("claude-sonnet-5-5", 7)])
        self.assertEqual(c[0].model, "claude-opus-5-5")

    def test_the_routing_verdict_follows_the_terminal_chunk_in_both_orders(self):
        self._chunks("ta", "claude-opus-5-5", "claude-sonnet-5-5")
        self._chunks("tb", "claude-sonnet-5-5", "claude-opus-5-5")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual([v["label"] for v in r["violations"]], ["tb"])
        self.assertEqual(r["violations"][0]["kinds"], ["MISMATCH"])
        # both groups disagreed about the model: informational, never a verdict
        self.assertEqual(r["counts"]["chunk_model_splits"], 2)
        self.assertIn("chunk_model_splits=2", "\n".join(cct._routing_lines(r)))

    def test_chunk_splits_alone_never_change_a_green_verdict(self):
        self._chunks("tc", "claude-opus-5-5", "claude-sonnet-5-5")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["counts"]["chunk_model_splits"], 1)


class RoutingUnprovableTerminalTests(_RoutingFixture):
    """Cross-model review round 2, P1: a chunk WITHOUT ``output_tokens``
    cannot be ranked, so when it shares a ``message.id`` with chunks that
    name ANOTHER model the terminal chunk cannot be elected from complete
    information. That group used to lose the usage-less chunk silently and
    could end GREEN; it is now INCONCLUSIVE and named, in both orders."""

    def _group(self, agent_id, chunks, *, archetype="code-reviewer", model="claude-fable-5"):
        """One spawn whose chunks share ONE message.id. Each chunk is
        (model, output_tokens-or-None); None writes ``usage: null``."""
        base = self.spawn(
            agent_id,
            {"agentType": archetype, "description": agent_id, "model": model},
            None,
        )
        lines = []
        for i, (served, out) in enumerate(chunks):
            rec = json.loads(
                _assistant_line(
                    msg_id="msg_group_" + agent_id,
                    model=served,
                    ts=self.now + timedelta(seconds=i),
                    usage=_usage(input_tokens=1, output_tokens=out or 0),
                    session_id="sess-1",
                )
            )
            if out is None:
                rec["message"]["usage"] = None
            lines.append(json.dumps(rec))
        (base / ("agent-%s.jsonl" % agent_id)).write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def _assert_unprovable(self, r):
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 1)
        self.assertIn("terminal chunk cannot be proven", r["reason"])
        self.assertEqual(cct.routing_rc(r), cct.ROUTING_RC_NOT_PROVEN)

    def test_a_later_usage_less_divergent_chunk_is_INCONCLUSIVE_not_GREEN(self):
        self._group("p1", [("claude-fable-5", 7), ("claude-sonnet-5-5", None)])
        self._assert_unprovable(self.run_routing())

    def test_an_earlier_usage_less_divergent_chunk_is_INCONCLUSIVE_not_GREEN(self):
        self._group("p2", [("claude-sonnet-5-5", None), ("claude-fable-5", 7)])
        self._assert_unprovable(self.run_routing())

    def test_with_the_usage_filled_in_the_terminal_is_elected_and_it_is_RED(self):
        # the SAME group once the divergent chunk carries its usage: the
        # check is complete, so the verdict is a violation, not "unsure".
        self._group("p3", [("claude-fable-5", 7), ("claude-sonnet-5-5", 9)])
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED", r["reason"])
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 0)
        self.assertEqual(r["violations"][0]["kinds"], ["MISMATCH", "FLOOR_BREACH"])

    def test_a_partial_usage_without_output_tokens_cannot_be_ranked_either(self):
        base = self.spawn(
            "p4",
            {"agentType": "general-purpose", "description": "p4", "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
        )
        rec = json.loads(
            _assistant_line(
                msg_id="msg_p4_0",
                model="claude-opus-5-5",
                ts=self.now + timedelta(seconds=9),
                usage=_usage(input_tokens=1, output_tokens=1),
                session_id="sess-1",
            )
        )
        rec["message"]["usage"] = {"input_tokens": 5}
        with (base / "agent-p4.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        self._assert_unprovable(self.run_routing())

    def test_a_usage_less_chunk_that_agrees_on_the_model_is_not_a_split(self):
        self._group("p5", [("claude-fable-5", 7), ("claude-fable-5", None)])
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["counts"]["chunk_model_splits"], 0)
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 0)

    def test_a_complete_disagreement_stays_informational(self):
        self._group("p6", [("claude-opus-5", 7), ("claude-fable-5", 7)])
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["counts"]["chunk_model_splits"], 1)
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 0)

    def test_a_real_violation_outranks_the_unprovable_group(self):
        self._group("p7", [("claude-fable-5", 7), ("claude-sonnet-5-5", None)])
        self.spawn(
            "bad",
            {"agentType": "general-purpose", "description": "bad", "model": "haiku"},
            self.turns("claude-opus-5-5"),
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED", r["reason"])
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 1)

    def _assert_no_violation_from_the_unprovable_group(self, r):
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 1)
        self.assertEqual(r["counts"]["compared_spawns"], 0)
        self.assertEqual(cct.routing_rc(r), cct.ROUTING_RC_NOT_PROVEN)

    def test_cross_model_round3_counterexample_sonnet_then_usage_less_fable(self):
        # Codex round 3: a `code-reviewer` declared Fable, one message.id,
        # Sonnet (output_tokens=7) then Fable with `usage: null`. The guessed
        # terminal used to be Sonnet and the group raised RED, rc 1,
        # MISMATCH + FLOOR_BREACH although the terminal cannot be proven.
        self._group("c1", [("claude-sonnet-5-5", 7), ("claude-fable-5", None)])
        self._assert_no_violation_from_the_unprovable_group(self.run_routing())

    def test_cross_model_round3_counterexample_in_the_other_order(self):
        self._group("c2", [("claude-fable-5", None), ("claude-sonnet-5-5", 7)])
        self._assert_no_violation_from_the_unprovable_group(self.run_routing())

    def test_the_same_group_with_complete_usage_elects_its_terminal(self):
        # contrast: once every chunk carries output_tokens the terminal is
        # elected (tie -> the later chunk, Fable) and the check is complete
        self._group("c3", [("claude-sonnet-5-5", 7), ("claude-fable-5", 7)])
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 0)
        self.assertEqual(r["counts"]["chunk_model_splits"], 1)

    def test_a_proven_violation_beside_an_uncertain_group_stays_RED(self):
        # ONE spawn, two message groups: g1 is a single proven Opus turn
        # (violates the declared Haiku); g2 is the uncertain group. RED comes
        # from g1 ALONE -- g2's models are not in the evidence -- and the
        # uncertain group is still named.
        base = self.spawn(
            "mix",
            {"agentType": "general-purpose", "description": "mix", "model": "haiku"},
            None,
        )
        lines = []
        for msg_id, model, out, i in (
            ("msg_g1", "claude-opus-5-5", 5, 0),
            ("msg_g2", "claude-haiku-4-5-20251001", 7, 1),
            ("msg_g2", "claude-sonnet-5-5", None, 2),
        ):
            rec = json.loads(
                _assistant_line(
                    msg_id=msg_id,
                    model=model,
                    ts=self.now + timedelta(seconds=i),
                    usage=_usage(input_tokens=1, output_tokens=out or 0),
                    session_id="sess-1",
                )
            )
            if out is None:
                rec["message"]["usage"] = None
            lines.append(json.dumps(rec))
        (base / "agent-mix.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        r = self.run_routing()
        self.assertEqual(r["verdict"], "RED", r["reason"])
        self.assertEqual(cct.routing_rc(r), cct.ROUTING_RC_RED)
        self.assertEqual(len(r["violations"]), 1)
        v = r["violations"][0]
        self.assertEqual(v["kinds"], ["MISMATCH"])
        self.assertEqual(v["served"], {"claude-opus-5-5": 1})
        self.assertEqual(r["counts"]["chunk_terminal_unprovable"], 1)

    def test_an_uncertain_group_cannot_vouch_for_a_spawn_either(self):
        # the other direction: the only turns are the uncertain group's, one
        # of which matches the declaration -- that is not a pass
        self._group(
            "c4", [("claude-fable-5", 7), ("claude-sonnet-5-5", None)], archetype="general-purpose"
        )
        r = self.run_routing()
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertEqual(r["counts"]["compared_spawns"], 0)

    def test_the_cost_totals_do_not_move(self):
        self._group("p8", [("claude-fable-5", 7), ("claude-sonnet-5-5", None)])
        rolled = cct.transcript_rollup(self.corpus, cutoff=None, by="model")
        # only the billed chunk is a cost turn; the verdict is the routing's
        self.assertEqual(rolled["grand_total"]["turns"], 1)
        self.assertEqual(rolled["routing"]["verdict"], "INCONCLUSIVE")


class RoutingStaleDeclarationsTests(_RoutingFixture):
    """Cross-model review P2-2: a declaration the check cannot classify (or
    a sidecar it cannot read) used to be counted BEFORE the window filter, so
    one stale spawn left every newer window INCONCLUSIVE."""

    OLD = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)

    def _old_odd_spawn(self, agent_id="old", model="opusplan"):
        self.spawn(
            agent_id,
            {"agentType": "general-purpose", "description": agent_id, "model": model},
            [("claude-opus-5-5", self.OLD)],
        )

    def _fresh_good_spawn(self):
        self.spawn(
            "new",
            {"agentType": "general-purpose", "description": "new", "model": "haiku"},
            self.turns("claude-haiku-4-5-20251001"),
        )

    def test_a_stale_unclassified_declaration_does_not_gate_a_newer_window(self):
        self._old_odd_spawn()
        self._fresh_good_spawn()
        wide = self.run_routing()
        self.assertEqual(wide["verdict"], "INCONCLUSIVE")
        self.assertEqual(wide["counts"]["unclassified"], 1)
        week = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(week["verdict"], "GREEN", week["reason"])
        self.assertEqual(week["counts"]["unclassified"], 0)
        self.assertEqual(week["counts"]["out_of_window"], 1)
        self.assertEqual(week["unclassified_samples"], [])

    def test_a_stale_unreadable_sidecar_does_not_gate_a_newer_window(self):
        base = self.spawn(
            "old", {"agentType": "general-purpose", "description": "old"}, [("claude-opus-5-5", self.OLD)]
        )
        (base / "agent-old.meta.json").write_text("{not json", encoding="utf-8")
        self._fresh_good_spawn()
        self.assertEqual(self.run_routing()["verdict"], "INCONCLUSIVE")
        week = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(week["verdict"], "GREEN", week["reason"])
        self.assertEqual(week["counts"]["unreadable_sidecars"], 0)

    def test_an_odd_declaration_that_was_never_served_gates_nothing(self):
        # no transcript at all: nothing was served, so nothing can have been
        # routed wrongly
        self.spawn(
            "ghost",
            {"agentType": "general-purpose", "description": "ghost", "model": "opusplan"},
            None,
        )
        self._fresh_good_spawn()
        r = self.run_routing()
        self.assertEqual(r["verdict"], "GREEN", r["reason"])
        self.assertEqual(r["counts"]["unclassified"], 0)
        self.assertEqual(r["counts"]["no_served"], 1)

    def test_an_unplaceable_stale_spawn_still_fails_closed(self):
        # the only line of the old transcript is torn: nothing proves it is
        # outside the window, so the odd declaration keeps gating
        base = self.spawn(
            "torn",
            {"agentType": "general-purpose", "description": "torn", "model": "opusplan"},
            [],
            raw_lines=['{"type": "assistant", "message": {"usage": '],
        )
        self.assertTrue((base / "agent-torn.jsonl").exists())
        self._fresh_good_spawn()
        week = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(week["verdict"], "INCONCLUSIVE", week["reason"])
        self.assertEqual(week["counts"]["unclassified"], 1)

    def test_an_in_window_unclassified_declaration_still_gates(self):
        self.spawn(
            "odd",
            {"agentType": "general-purpose", "description": "odd", "model": "opusplan"},
            self.turns("claude-opus-5-5"),
        )
        self._fresh_good_spawn()
        r = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["counts"]["unclassified"], 1)


class RoutingProvablyOutOfWindowTests(_RoutingFixture):
    """Cross-model review round 2, P2: an unreadable record with a VALID
    timestamp outside the window used to be counted as incompleteness before
    the window filter ran, so a stale ``message: null`` left every newer
    window INCONCLUSIVE. Only what has no temporal position (or sits inside
    the window) may."""

    OLD = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    FUTURE = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _null_message(self, when):
        return json.dumps(
            {
                "type": "assistant",
                "timestamp": None if when is None else _iso(when),
                "message": None,
            }
        )

    def _good_with_stray(self, when, agent_id="g1"):
        return self.spawn(
            agent_id,
            {"agentType": "general-purpose", "description": agent_id, "model": "sonnet"},
            self.turns("claude-sonnet-5-5"),
            raw_lines=[self._null_message(when)],
        )

    def test_a_stale_unreadable_record_does_not_gate_a_newer_window(self):
        self._good_with_stray(self.OLD)
        wide = self.run_routing()
        self.assertEqual(wide["verdict"], "INCONCLUSIVE", wide["reason"])
        self.assertEqual(wide["counts"]["incomplete_reads"], 1)
        week = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(week["verdict"], "GREEN", week["reason"])
        self.assertEqual(week["counts"]["incomplete_reads"], 0)

    def test_a_record_after_the_upper_bound_does_not_gate_either(self):
        self._good_with_stray(self.FUTURE)
        closed = self.run_routing(until=self.now + timedelta(hours=1))
        self.assertEqual(closed["verdict"], "GREEN", closed["reason"])
        self.assertEqual(closed["counts"]["incomplete_reads"], 0)
        self.assertEqual(self.run_routing()["verdict"], "INCONCLUSIVE")

    def test_an_unreadable_record_inside_the_window_still_gates(self):
        self._good_with_stray(self.now - timedelta(hours=1))
        r = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertEqual(r["counts"]["incomplete_reads"], 1)

    def test_an_unreadable_record_with_no_timestamp_has_no_position_so_it_gates(self):
        self._good_with_stray(None)
        r = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(r["verdict"], "INCONCLUSIVE", r["reason"])
        self.assertEqual(r["counts"]["incomplete_reads"], 1)

    def test_the_same_holds_for_a_stale_spawn_with_an_odd_declaration(self):
        # a spawn whose ONLY record is a stale unreadable one: an
        # unclassifiable declaration and an unreadable sidecar on it must
        # not gate a newer window either
        self.spawn(
            "odd",
            {"agentType": "general-purpose", "description": "odd", "model": "opusplan"},
            [],
            raw_lines=[self._null_message(self.OLD)],
        )
        base = self.spawn(
            "bad",
            {"agentType": "general-purpose", "description": "bad"},
            [],
            raw_lines=[self._null_message(self.OLD)],
        )
        (base / "agent-bad.meta.json").write_text("{not json", encoding="utf-8")
        self.spawn(
            "new",
            {"agentType": "general-purpose", "description": "new", "model": "haiku"},
            self.turns("claude-haiku-4-5-20251001"),
        )
        week = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(week["verdict"], "GREEN", week["reason"])
        self.assertEqual(week["counts"]["out_of_window"], 2)
        self.assertEqual(week["counts"]["unclassified"], 0)
        self.assertEqual(week["counts"]["unreadable_sidecars"], 0)
        # ... while a wide window sees both
        wide = self.run_routing()
        self.assertEqual(wide["verdict"], "INCONCLUSIVE")
        self.assertEqual(wide["counts"]["unclassified"], 1)
        self.assertEqual(wide["counts"]["unreadable_sidecars"], 1)

    def test_a_stale_unreadable_record_in_an_otherwise_empty_spawn_is_a_turn_outside(self):
        # `none` (no turn at all) and `out` (a turn exists, outside) are
        # different placements: this record IS a turn, positioned outside.
        base = self.spawn(
            "only",
            {"agentType": "general-purpose", "description": "only"},
            [],
            raw_lines=[self._null_message(self.OLD)],
        )
        (base / "agent-only.meta.json").write_text("[1]", encoding="utf-8")
        r = self.run_routing(cutoff=self.now - timedelta(days=7))
        self.assertEqual(r["counts"]["out_of_window"], 1)
        self.assertEqual(r["counts"]["no_served"], 0)


class RoutingPreRegistrationTests(TestEnvContext):
    """The death criteria are pre-registered in the module docstring; a
    later edit that quietly deletes or softens one fails here, so a change
    to a number is a visible decision and never an edit in passing."""

    def test_every_criterion_and_its_number_is_in_the_docstring(self):
        doc = cct.__doc__ or ""
        for marker in ("K-A1", "K-A2", "K-A3", "K-B1", "K-B2"):
            self.assertIn(marker, doc, marker)
        self.assertIn("PRE-REGISTERED DEATH CRITERIA", doc)
        self.assertIn(">= 20 spawn sidecars", doc)
        self.assertIn("three DISTINCT violations", doc)
        self.assertIn("ONE control spawn", doc)
        self.assertIn("restarts, from zero", doc)
        # whitespace-normalised: a re-wrap of the docstring is not an edit
        self.assertIn("deliberately no suppression list", " ".join(doc.split()))

    def test_the_pointer_names_every_criterion(self):
        for marker in ("K-A1", "K-A3", "K-B1", "K-B2"):
            self.assertIn(marker, cct.ROUTING_PREREG_POINTER)

    def test_there_is_no_suppression_list_in_the_detector(self):
        # A tripwire, not a proof: K-A3 says the detector has NO way to
        # mute a finding, so the routing section may not grow one under any
        # of the obvious names.
        src = (Path(cct.__file__)).read_text(encoding="utf-8")
        start = src.index("# Routing invariant (PLAN-186 AC-13) -- contract")
        end = src.index("# Programmatic API (PLAN-186 W0, AC-1b)")
        body = src[start:end].lower()
        for word in ("suppress", "waive", "ignore_label", "skip_label", "exempt", "silence"):
            self.assertNotIn(word, body, word)


if __name__ == "__main__":
    unittest.main()
