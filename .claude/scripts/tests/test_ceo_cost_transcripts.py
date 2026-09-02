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

    def test_load_pricing_default_applies_ratified_sonnet5_override(self):
        # Default path (pricing_arg=None) resolves the in-repo
        # cost-table.yaml, which still carries the pre-intro $3/$15
        # Sonnet 5 row (S337/S338 note) — the ratified $2/$10 correction
        # must be layered on top when the DEFAULT path is used.
        result = cct.load_pricing(None)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.table["claude-sonnet-5"]["input_per_mtok"], 2.00)
        self.assertEqual(result.table["claude-sonnet-5"]["output_per_mtok"], 10.00)
        self.assertIn("ratified correction", result.source)

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


if __name__ == "__main__":
    unittest.main()
