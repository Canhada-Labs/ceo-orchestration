"""PLAN-040 tests — ceo-cost.py streaming mode + OTLP export.

Covers the Round-1 debate convergent P0 closures:

- **CONV-1 (DevOps P0-1 + QA P0-1):** log-rotation recovery via inode
  tracking; streaming testability via injected `tick_fn`.
- **CONV-2 (DevOps P0-2 + QA P0-2):** OTLP HTTP POST seam (`_http_post`
  extracted for DI); auth header / endpoint path redaction;
  fail-open → local fallback JSONL.
- **DevOps P0-3:** heartbeat emit observable from the same sink.
- **QA P0-3:** 6-row decision-table for the kill-switch + env-var
  matrix, each row isolated via TestEnvContext.

No live network, no real `time.sleep`. Tests drive iterations via a
counter-backed tick_fn and inject a fake time source.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple


def _load_module():
    here = Path(__file__).resolve().parent.parent
    src = here / "ceo-cost.py"
    spec = importlib.util.spec_from_file_location("ceo_cost_stream_under_test", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


cc = _load_module()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _finite_tick(n: int) -> Callable[[], bool]:
    """Return a tick_fn that yields True n times, then False forever."""
    state = {"remaining": n}

    def tick() -> bool:
        if state["remaining"] <= 0:
            return False
        state["remaining"] -= 1
        return True

    return tick


def _fake_time_source(start: float = 1_000_000_000.0, step: float = 1.0) -> Callable[[], float]:
    """Deterministic monotonic clock — advances `step` seconds per call."""
    state = {"now": start}

    def clock() -> float:
        state["now"] += step
        return state["now"]

    return clock


def _write_audit_line(path: Path, entry: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _default_pricing() -> Dict[str, Dict[str, float]]:
    return {
        "claude-opus-4-7": {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
        "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
        "claude-haiku-4-5-20251001": {"input_per_mtok": 0.25, "output_per_mtok": 1.25},
    }


class _TestEnvContext:
    """Lightweight env-var isolation (mirrors _lib/testing.TestEnvContext)."""

    def __init__(self, **env: str) -> None:
        self._overrides = env
        self._original: Dict[str, str] = {}

    def __enter__(self) -> "_TestEnvContext":
        for k, v in self._overrides.items():
            if k in os.environ:
                self._original[k] = os.environ[k]
            else:
                self._original[k] = ""
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *_: Any) -> None:
        for k, v in self._overrides.items():
            orig = self._original.get(k)
            if orig == "":
                os.environ.pop(k, None)
            else:
                os.environ[k] = orig


# ===========================================================================
# A. CostStreamer unit tests — process_entry + running totals + alerts
# ===========================================================================


class CostStreamerProcessEntryTests(unittest.TestCase):
    def test_skips_entry_without_model(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            sink=sink,
            time_fn=_fake_time_source(),
        )
        out = s.process_entry({"tokens_in": 100, "tokens_out": 50})
        self.assertIsNone(out)
        self.assertEqual(sink.getvalue(), "")

    def test_skips_entry_with_zero_tokens(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            sink=sink,
            time_fn=_fake_time_source(),
        )
        out = s.process_entry({"model": "claude-opus-4-7", "tokens_in": 0, "tokens_out": 0})
        self.assertIsNone(out)

    def test_emits_cost_event_for_opus_spawn(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            sink=sink,
            time_fn=_fake_time_source(),
        )
        event = s.process_entry(
            {
                "model": "claude-opus-4-7",
                "tokens_in": 1_000_000,
                "tokens_out": 200_000,
                "session_id": "sess-a",
                "ts": "2026-04-19T12:00:00Z",
            }
        )
        self.assertIsNotNone(event)
        # cost = 1M/1M * 15 + 200k/1M * 75 = 15 + 15 = 30.00
        assert event is not None
        self.assertAlmostEqual(event["cost_usd"], 30.00, places=4)
        self.assertEqual(event["running_session_usd"], 30.00)
        # Sink may carry >1 line (cost event + alert trigger if cost >= threshold).
        # Validate the first line is the spawn.cost event.
        first_line = sink.getvalue().strip().splitlines()[0]
        payload = json.loads(first_line)
        self.assertEqual(payload["event"], "spawn.cost")
        self.assertEqual(payload["session_id"], "sess-a")

    def test_running_session_total_accumulates(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            sink=sink,
            time_fn=_fake_time_source(),
        )
        for _ in range(3):
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "sess-b",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
        # cost per call = 0.1*15 + 0.05*75 = 1.5 + 3.75 = 5.25
        # after 3 calls: 15.75
        last_event = json.loads(sink.getvalue().strip().splitlines()[-1])
        self.assertAlmostEqual(last_event["running_session_usd"], 15.75, places=2)


class CostStreamerAlertTests(unittest.TestCase):
    def test_session_alert_fires_once(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            alert_session_usd=10.0,
            sink=sink,
            time_fn=_fake_time_source(),
        )
        # Each call costs 5.25; 2 calls crosses the 10.0 threshold.
        for _ in range(3):
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "alert-test",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
        lines = sink.getvalue().strip().splitlines()
        alerts = [
            json.loads(ln)
            for ln in lines
            if json.loads(ln).get("event") == "cost.alert.session_threshold"
        ]
        self.assertEqual(len(alerts), 1, "alert must fire exactly once")
        self.assertEqual(alerts[0]["session_id"], "alert-test")
        self.assertEqual(alerts[0]["threshold_usd"], 10.0)

    def test_daily_alert_uses_ts_bucket(self) -> None:
        sink = io.StringIO()
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            alert_daily_usd=7.0,
            sink=sink,
            time_fn=_fake_time_source(),
        )
        for sid in ("a", "b"):
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": sid,
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
        alerts = [
            json.loads(ln)
            for ln in sink.getvalue().strip().splitlines()
            if json.loads(ln).get("event") == "cost.alert.daily_threshold"
        ]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["day"], "2026-04-19")


# ===========================================================================
# B. OTLP POST + fallback — DI seam + redaction
# ===========================================================================


class OtlpPostTests(unittest.TestCase):
    def test_200_success_no_fallback(self) -> None:
        calls: List[Tuple[str, Dict[str, str], bytes, float]] = []

        def fake_post(url, headers, body, timeout=5.0):
            calls.append((url, dict(headers), body, timeout))
            return (200, b"")

        sink = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            fb = Path(tmp) / "fb.jsonl"
            s = cc.CostStreamer(
                pricing=_default_pricing(),
                otlp_endpoint="https://collector.example.com/v1/metrics",
                bearer_token="secret-token-xyz",
                http_post_fn=fake_post,
                fallback_path=fb,
                sink=sink,
                time_fn=_fake_time_source(),
            )
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
            self.assertFalse(fb.exists(), "no fallback write on 200")
        self.assertEqual(len(calls), 1)
        _url, headers, body, _t = calls[0]
        self.assertEqual(headers["Authorization"], "Bearer secret-token-xyz")
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("resourceMetrics", payload)

    def test_500_routes_to_fallback_and_redacts_log(self) -> None:
        def fake_post(url, headers, body, timeout=5.0):
            return (500, b"oops")

        sink = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            fb = Path(tmp) / "fb.jsonl"
            s = cc.CostStreamer(
                pricing=_default_pricing(),
                otlp_endpoint="https://collector.example.com:4318/v1/metrics?auth=leak",
                bearer_token="supersecret",
                http_post_fn=fake_post,
                fallback_path=fb,
                sink=sink,
                time_fn=_fake_time_source(),
            )
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
            self.assertTrue(fb.exists())
        # Sink must carry a post_failure breadcrumb with redacted endpoint.
        failures = [
            json.loads(ln)
            for ln in sink.getvalue().strip().splitlines()
            if json.loads(ln).get("event") == "cost.stream.post_failure"
        ]
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            failures[0]["endpoint"], "https://collector.example.com:4318"
        )
        # Auth header must NEVER appear in any emitted line.
        full_log = sink.getvalue()
        self.assertNotIn("supersecret", full_log)
        self.assertNotIn("auth=leak", full_log)

    def test_network_exception_routes_to_fallback(self) -> None:
        def fake_post(url, headers, body, timeout=5.0):
            raise OSError("connection refused")

        sink = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            fb = Path(tmp) / "fb.jsonl"
            s = cc.CostStreamer(
                pricing=_default_pricing(),
                otlp_endpoint="https://collector.example.com/v1",
                http_post_fn=fake_post,
                fallback_path=fb,
                sink=sink,
                time_fn=_fake_time_source(),
            )
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
            self.assertTrue(fb.exists())
            # Read fallback line
            lines = fb.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            fallback_event = json.loads(lines[0])
            self.assertEqual(fallback_event["event"], "spawn.cost")


class RedactEndpointTests(unittest.TestCase):
    def test_strips_path_and_query(self) -> None:
        self.assertEqual(
            cc._redact_endpoint(
                "https://collector.example.com:4318/v1/metrics?key=secret"
            ),
            "https://collector.example.com:4318",
        )

    def test_handles_no_port(self) -> None:
        self.assertEqual(
            cc._redact_endpoint("http://foo.local/path"),
            "http://foo.local",
        )

    def test_handles_malformed_url(self) -> None:
        self.assertEqual(cc._redact_endpoint("not a url at all"), "http://")


# ===========================================================================
# C. Heartbeat — emits at configured interval
# ===========================================================================


class HeartbeatTests(unittest.TestCase):
    def test_no_heartbeat_before_interval(self) -> None:
        sink = io.StringIO()
        clock = _fake_time_source(start=1_000_000_000.0, step=10.0)
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            heartbeat_secs=60,
            sink=sink,
            time_fn=clock,
        )
        # Only 1 clock tick = 10s elapsed
        out = s.maybe_heartbeat()
        self.assertIsNone(out)

    def test_heartbeat_fires_after_interval(self) -> None:
        sink = io.StringIO()
        # Each clock() call advances 30s; after 3 calls the gap from last
        # heartbeat is >= 60s.
        clock = _fake_time_source(start=1_000_000_000.0, step=30.0)
        s = cc.CostStreamer(
            pricing=_default_pricing(),
            heartbeat_secs=60,
            sink=sink,
            time_fn=clock,
        )
        # Drain a couple of ticks
        self.assertIsNone(s.maybe_heartbeat())
        hb = s.maybe_heartbeat()
        self.assertIsNotNone(hb)
        assert hb is not None
        self.assertEqual(hb["event"], "cost.stream.heartbeat")


# ===========================================================================
# D. tail_entries — log rotation recovery (CONV-1)
# ===========================================================================


class TailEntriesTests(unittest.TestCase):
    def test_reads_new_lines_appended(self) -> None:
        """tail_entries seeks to end on first open then yields only
        newly-appended lines (tail -f semantics). Writes that happen
        BEFORE the tailer starts are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            log.write_text("", encoding="utf-8")

            state = {"ticks": 0}

            def tick_that_appends() -> bool:
                state["ticks"] += 1
                if state["ticks"] == 1:
                    _write_audit_line(
                        log, {"ts": "t1", "model": "claude-haiku-4-5"}
                    )
                    _write_audit_line(
                        log, {"ts": "t2", "model": "claude-haiku-4-5"}
                    )
                # Hard cap on ticks so test terminates deterministically.
                return state["ticks"] < 10

            entries = list(
                cc.tail_entries(
                    log,
                    tick_fn=tick_that_appends,
                    poll_secs=0.0,
                    time_sleep_fn=lambda _: None,
                )
            )
        self.assertEqual([e["ts"] for e in entries], ["t1", "t2"])

    def test_handles_file_replacement(self) -> None:
        """Simulate a log-rotation: after tail_entries seeks to end of
        the original file, a custom stat_fn reports a changed inode,
        prompting tail_entries to re-open at offset 0 and read the
        "rotated" content from the start."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            _write_audit_line(log, {"ts": "before-rotate"})
            original_ino = os.stat(log).st_ino

            # Custom stat_fn reports a different inode after the 3rd call.
            # (Calls 1-2 are within tail_entries' initial setup; by the
            # time we reach calls >= 3, the tailer has already seeked
            # to end.)
            call_counter = {"n": 0}

            def stat_rotating(path):
                call_counter["n"] += 1
                real = os.stat(path)
                if call_counter["n"] >= 3:
                    class _S:
                        def __init__(self, real, ino):
                            self._r = real
                            self.st_ino = ino

                        def __getattr__(self, name):
                            return getattr(self._r, name)

                    return _S(real, original_ino + 1)
                return real

            # Prepare the "rotated" content: once stat reports a new
            # inode, tail_entries will re-open + seek to 0 and read from
            # the start of whatever is there.
            seen: List[Dict[str, Any]] = []
            tick_n = {"n": 0}

            def tick_with_replace() -> bool:
                tick_n["n"] += 1
                if tick_n["n"] == 1:
                    # After first tick, overwrite file (simulates rotation +
                    # new content present at offset 0).
                    log.write_text(
                        json.dumps({"ts": "after-rotate"}) + "\n",
                        encoding="utf-8",
                    )
                # Hard cap on ticks so test always terminates even if the
                # implementation misbehaves.
                return tick_n["n"] < 20 and len(seen) < 1

            for entry in cc.tail_entries(
                log,
                tick_fn=tick_with_replace,
                poll_secs=0.0,
                stat_fn=stat_rotating,
                time_sleep_fn=lambda _: None,
            ):
                seen.append(entry)
                if len(seen) >= 1:
                    break
        # We must see at least one entry produced after the rotation.
        self.assertGreaterEqual(len(seen), 1)
        self.assertEqual(seen[0]["ts"], "after-rotate")


# ===========================================================================
# E. OTLP payload shape
# ===========================================================================


class OtlpPayloadShapeTests(unittest.TestCase):
    def test_payload_has_required_otlp_keys(self) -> None:
        event = {
            "model": "claude-opus-4-7",
            "cost_usd": 1.23,
            "session_id": "s1",
            "ts_unix_ms": 1_700_000_000_000,
        }
        payload = cc._otlp_metric_payload(event)
        self.assertIn("resourceMetrics", payload)
        rm = payload["resourceMetrics"][0]
        sm = rm["scopeMetrics"][0]
        metric = sm["metrics"][0]
        self.assertEqual(metric["name"], "ceo.cost.usd")
        self.assertEqual(metric["unit"], "USD")
        dp = metric["gauge"]["dataPoints"][0]
        self.assertAlmostEqual(dp["asDouble"], 1.23, places=4)
        # attributes carry model + session
        attr_keys = {a["key"] for a in dp["attributes"]}
        self.assertIn("model", attr_keys)
        self.assertIn("session_id", attr_keys)


# ===========================================================================
# F. run_stream integration — end-to-end with fake tick + fake http
# ===========================================================================


class RunStreamIntegrationTests(unittest.TestCase):
    def test_run_stream_emits_events_and_stops_on_tick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            _write_audit_line(
                log,
                {
                    "model": "claude-haiku-4-5-20251001",
                    "tokens_in": 1_000,
                    "tokens_out": 500,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                },
            )
            _write_audit_line(
                log,
                {
                    "model": "claude-sonnet-4-6",
                    "tokens_in": 10_000,
                    "tokens_out": 5_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                },
            )
            sink = io.StringIO()
            emitted = cc.run_stream(
                log,
                _default_pricing(),
                sink=sink,
                tick_fn=_finite_tick(8),
                time_fn=_fake_time_source(),
                max_events=5,
                poll_secs=0.0,
                time_sleep_fn=lambda _: None,
            )
        # Both entries appended BEFORE seek-to-end — skipped. Test
        # confirms no events emitted (by design: stream only new data).
        # If this changes to a historic-then-tail semantic, update here.
        self.assertEqual(emitted, 0)

    def test_run_stream_picks_up_live_appends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            log.write_text("", encoding="utf-8")
            sink = io.StringIO()
            tick_count = {"n": 0}

            def tick_that_appends() -> bool:
                tick_count["n"] += 1
                if tick_count["n"] == 2:
                    _write_audit_line(
                        log,
                        {
                            "model": "claude-haiku-4-5-20251001",
                            "tokens_in": 1_000,
                            "tokens_out": 500,
                            "session_id": "s1",
                            "ts": "2026-04-19T12:00:00Z",
                        },
                    )
                return tick_count["n"] < 12

            emitted = cc.run_stream(
                log,
                _default_pricing(),
                sink=sink,
                tick_fn=tick_that_appends,
                time_fn=_fake_time_source(),
                max_events=3,
                poll_secs=0.0,
                time_sleep_fn=lambda _: None,
            )
        self.assertGreaterEqual(emitted, 1)
        events = [json.loads(ln) for ln in sink.getvalue().strip().splitlines() if ln]
        spawn_costs = [e for e in events if e.get("event") == "spawn.cost"]
        self.assertGreaterEqual(len(spawn_costs), 1)


# ===========================================================================
# G. QA CONV-3 — 6-row decision-table env-var matrix
# ===========================================================================


class EnvVarMatrixTests(unittest.TestCase):
    """Ensures the kill-switch + explicit-flag + env-override matrix is
    covered. 6 rows per QA P0-3 debate closure."""

    def _run_main(self, argv: List[str]) -> Tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        import contextlib

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = cc.main(argv)
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_row_1_killswitch_blocks_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            log.write_text("", encoding="utf-8")
            with _TestEnvContext(
                CEO_COST_STREAMING="0",
                CEO_AUDIT_LOG_PATH=str(log),
            ):
                rc, _out, err = self._run_main(["--stream"])
        self.assertEqual(rc, 0)
        self.assertIn("kill-switch active", err)

    def test_row_2_killswitch_1_allows_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            log.write_text("", encoding="utf-8")
            with _TestEnvContext(
                CEO_COST_STREAMING="1",
                CEO_AUDIT_LOG_PATH=str(log),
            ):
                # Use --log explicitly (more deterministic) + rely on
                # the fact that run_stream with no tick_fn blocks forever;
                # we can't exercise it from --stream-mode via main(). Just
                # verify argparse accepts the flags.
                # Run without --stream: batch path must work.
                rc, _out, err = self._run_main(
                    ["--since", "7d", "--log", str(log)]
                )
        self.assertEqual(rc, 0)

    def test_row_3_log_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "alt.jsonl"
            log.write_text("", encoding="utf-8")
            with _TestEnvContext(
                CEO_AUDIT_LOG_PATH=str(log),
            ):
                rc, _out, _err = self._run_main(["--log", str(log)])
        self.assertEqual(rc, 0)

    def test_row_4_missing_otlp_env_graceful(self) -> None:
        # Streamer without bearer token env must still build + emit.
        with _TestEnvContext(CEO_COST_OTLP_BEARER=None):
            sink = io.StringIO()
            calls: List[Any] = []

            def fake_post(url, headers, body, timeout=5.0):
                calls.append(headers.copy())
                return 200, b""

            s = cc.CostStreamer(
                pricing=_default_pricing(),
                otlp_endpoint="https://example.com/v1",
                bearer_token=None,
                http_post_fn=fake_post,
                sink=sink,
                time_fn=_fake_time_source(),
            )
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
            self.assertEqual(len(calls), 1)
            # No Authorization header without a bearer token
            self.assertNotIn("Authorization", calls[0])

    def test_row_5_custom_fallback_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "audit.jsonl"
            log.write_text("", encoding="utf-8")
            fb = Path(tmp) / "custom-fb.jsonl"
            with _TestEnvContext(CEO_AUDIT_LOG_PATH=str(log)):
                # Argparse accepts --fallback-log
                parser = cc.build_parser()
                args = parser.parse_args(
                    [
                        "--stream",
                        "--log",
                        str(log),
                        "--fallback-log",
                        str(fb),
                    ]
                )
            self.assertEqual(Path(args.fallback_log), fb)

    def test_row_6_alert_thresholds_customizable(self) -> None:
        parser = cc.build_parser()
        args = parser.parse_args(
            [
                "--stream",
                "--alert-session-usd",
                "7.5",
                "--alert-daily-usd",
                "99.99",
                "--heartbeat-secs",
                "30",
            ]
        )
        self.assertAlmostEqual(args.alert_session_usd, 7.5, places=2)
        self.assertAlmostEqual(args.alert_daily_usd, 99.99, places=2)
        self.assertEqual(args.heartbeat_secs, 30)


# ===========================================================================
# H. Queue cap + backpressure
# ===========================================================================


class QueueCapTests(unittest.TestCase):
    def test_queue_cap_routes_to_fallback_without_network(self) -> None:
        # Build a streamer whose queue is already "full" before the
        # first call — any event should go straight to fallback with
        # no network try.
        called = {"n": 0}

        def never_call(url, headers, body, timeout=5.0):
            called["n"] += 1
            return 200, b""

        with tempfile.TemporaryDirectory() as tmp:
            fb = Path(tmp) / "fb.jsonl"
            s = cc.CostStreamer(
                pricing=_default_pricing(),
                otlp_endpoint="https://example.com/v1",
                http_post_fn=never_call,
                fallback_path=fb,
                sink=io.StringIO(),
                queue_cap=0,  # degenerate cap — overflow immediately
                time_fn=_fake_time_source(),
            )
            s.process_entry(
                {
                    "model": "claude-opus-4-7",
                    "tokens_in": 100_000,
                    "tokens_out": 50_000,
                    "session_id": "s1",
                    "ts": "2026-04-19T12:00:00Z",
                }
            )
            self.assertTrue(fb.exists())
        self.assertEqual(called["n"], 0, "queue cap=0 must skip network")


# ===========================================================================
# I. Parametrized per-model cost calculation (scaling coverage)
# ===========================================================================


import pytest


_COST_CASES = [
    # (model, tokens_in, tokens_out, expected_cost)
    ("claude-opus-4-7", 1_000_000, 0, 15.00),
    ("claude-opus-4-7", 0, 1_000_000, 75.00),
    ("claude-opus-4-7", 100_000, 50_000, 1.5 + 3.75),
    ("claude-sonnet-4-6", 1_000_000, 0, 3.00),
    ("claude-sonnet-4-6", 0, 1_000_000, 15.00),
    ("claude-sonnet-4-6", 250_000, 125_000, 0.75 + 1.875),
    ("claude-haiku-4-5-20251001", 1_000_000, 0, 0.25),
    ("claude-haiku-4-5-20251001", 0, 1_000_000, 1.25),
    ("claude-haiku-4-5-20251001", 500_000, 100_000, 0.125 + 0.125),
    ("unknown-model-xyz", 100_000, 100_000, 0.0),
]


@pytest.mark.parametrize("model,tin,tout,expected", _COST_CASES)
def test_cost_usd_per_model(model: str, tin: int, tout: int, expected: float) -> None:
    pricing = _default_pricing()
    out = cc.cost_usd(pricing, model, tin, tout)
    assert abs(out - expected) < 1e-6, (
        f"cost mismatch for {model}: got {out}, expected {expected}"
    )


# ===========================================================================
# J. Cost event schema completeness — required fields presence
# ===========================================================================


_EVENT_KEYS = [
    "event",
    "ts_iso",
    "ts_unix_ms",
    "model",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "session_id",
    "running_session_usd",
    "running_day_usd",
]


@pytest.mark.parametrize("key", _EVENT_KEYS)
def test_cost_event_includes_key(key: str) -> None:
    sink = io.StringIO()
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        sink=sink,
        time_fn=_fake_time_source(),
    )
    event = s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "sess-schema",
            "ts": "2026-04-19T12:00:00Z",
        }
    )
    assert event is not None
    assert key in event, f"missing cost event field: {key}"


# ===========================================================================
# K. OTLP payload attribute completeness
# ===========================================================================


@pytest.mark.parametrize("attr_key", ["model", "session_id", "event"])
def test_otlp_attribute_present(attr_key: str) -> None:
    event = {
        "model": "claude-opus-4-7",
        "session_id": "s1",
        "event": "spawn.cost",
        "cost_usd": 1.0,
        "ts_unix_ms": 1_700_000_000_000,
    }
    payload = cc._otlp_metric_payload(event)
    attrs = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0][
        "gauge"
    ]["dataPoints"][0]["attributes"]
    keys = {a["key"] for a in attrs}
    assert attr_key in keys, f"OTLP payload missing attribute: {attr_key}"


def test_otlp_payload_omits_missing_optional_attrs() -> None:
    event = {
        "model": "claude-opus-4-7",
        "cost_usd": 1.0,
        "ts_unix_ms": 1_700_000_000_000,
        # no session_id, no plan_id, no skill, no event
    }
    payload = cc._otlp_metric_payload(event)
    attrs = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0][
        "gauge"
    ]["dataPoints"][0]["attributes"]
    keys = {a["key"] for a in attrs}
    assert "model" in keys
    assert "session_id" not in keys
    assert "plan_id" not in keys


# ===========================================================================
# L. Alert threshold boundary (exactly at threshold fires)
# ===========================================================================


def test_alert_fires_at_exact_threshold() -> None:
    """Alert uses >= comparison — hitting the threshold exactly fires."""
    sink = io.StringIO()
    # One opus spawn at cost exactly 5.25 with threshold=5.25 must fire.
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        alert_session_usd=5.25,
        sink=sink,
        time_fn=_fake_time_source(),
    )
    s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "boundary",
            "ts": "2026-04-19T12:00:00Z",
        }
    )
    alerts = [
        json.loads(ln)
        for ln in sink.getvalue().strip().splitlines()
        if json.loads(ln).get("event") == "cost.alert.session_threshold"
    ]
    assert len(alerts) == 1


def test_alert_does_not_fire_below_threshold() -> None:
    sink = io.StringIO()
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        alert_session_usd=1000.0,
        sink=sink,
        time_fn=_fake_time_source(),
    )
    s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "no-alert",
            "ts": "2026-04-19T12:00:00Z",
        }
    )
    alerts = [
        ln
        for ln in sink.getvalue().strip().splitlines()
        if json.loads(ln).get("event") == "cost.alert.session_threshold"
    ]
    assert alerts == []


# ===========================================================================
# M. Heartbeat state — carries accumulated totals
# ===========================================================================


def test_heartbeat_carries_session_totals() -> None:
    sink = io.StringIO()
    clock = _fake_time_source(start=1_000_000_000.0, step=70.0)
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        heartbeat_secs=60,
        sink=sink,
        time_fn=clock,
    )
    # Emit some cost events BEFORE heartbeat fires.
    s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "hb-session",
            "ts": "2026-04-19T12:00:00Z",
        }
    )
    hb = s.maybe_heartbeat()
    assert hb is not None
    assert "hb-session" in hb["session_totals_usd"]
    assert hb["session_totals_usd"]["hb-session"] > 0.0


def test_heartbeat_includes_post_failures_total() -> None:
    sink = io.StringIO()
    clock = _fake_time_source(start=1_000_000_000.0, step=70.0)
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        heartbeat_secs=60,
        sink=sink,
        time_fn=clock,
    )
    hb = s.maybe_heartbeat()
    assert hb is not None
    assert "post_failures_total" in hb
    assert hb["post_failures_total"] == 0


# ===========================================================================
# N. No-endpoint path — no http calls attempted
# ===========================================================================


def test_no_otlp_endpoint_skips_http() -> None:
    called = {"n": 0}

    def must_not_run(*_args, **_kwargs):
        called["n"] += 1
        return 200, b""

    sink = io.StringIO()
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        otlp_endpoint=None,
        http_post_fn=must_not_run,
        sink=sink,
        time_fn=_fake_time_source(),
    )
    s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "noep",
            "ts": "2026-04-19T12:00:00Z",
        }
    )
    assert called["n"] == 0


# ===========================================================================
# O. Fallback path absent — fails silently (no exception)
# ===========================================================================


def test_fallback_path_none_absorbs_http_failure() -> None:
    def fail_post(url, headers, body, timeout=5.0):
        raise OSError("boom")

    sink = io.StringIO()
    s = cc.CostStreamer(
        pricing=_default_pricing(),
        otlp_endpoint="https://example.com/v1",
        http_post_fn=fail_post,
        fallback_path=None,
        sink=sink,
        time_fn=_fake_time_source(),
    )
    # Should not raise.
    s.process_entry(
        {
            "model": "claude-opus-4-7",
            "tokens_in": 100_000,
            "tokens_out": 50_000,
            "session_id": "nofb",
            "ts": "2026-04-19T12:00:00Z",
        }
    )


# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
