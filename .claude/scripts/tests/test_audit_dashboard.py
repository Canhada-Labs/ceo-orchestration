"""Unit tests for audit-dashboard.py — read-only SSE dashboard."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import via filename since the script has a dash
import importlib.util

_SCRIPT = Path(__file__).resolve().parent.parent / "audit-dashboard.py"
_spec = importlib.util.spec_from_file_location("audit_dashboard", _SCRIPT)
audit_dashboard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_dashboard)


class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dash-test-")
        self.log = Path(self.tmp) / "audit-log.jsonl"
        # Restore CEO_AUDIT_LOG_PATH on teardown so this plain TestCase does not
        # leak a stale value into later tests in the sequential scripts pass.
        self.addCleanup(
            lambda _p=os.environ.get("CEO_AUDIT_LOG_PATH"):
            os.environ.__setitem__("CEO_AUDIT_LOG_PATH", _p) if _p is not None
            else os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        )
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log)

        # Seed log with a couple of events
        self.log.write_text(
            json.dumps({"ts": "2026-04-12T10:00:00Z", "action": "agent_spawn", "skill": "test"}) + "\n" +
            json.dumps({"ts": "2026-04-12T10:00:01Z", "action": "veto_triggered", "reason_code": "missing_skill"}) + "\n"
        )

        # Start server on random port
        token = "test-token-" + str(os.getpid())
        state = audit_dashboard.DashboardState(
            token=token, log_path=self.log, tail_n=10, max_connections=4
        )
        handler = audit_dashboard._make_handler(state)
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.token = token
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)

    def _url(self, path: str, token: str = None) -> str:
        t = token if token is not None else self.token
        sep = "&" if "?" in path else "?"
        return f"http://127.0.0.1:{self.port}{path}{sep}t={t}"

    def test_root_returns_html_with_token(self):
        with urllib.request.urlopen(self._url("/"), timeout=2) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            self.assertIn("<!DOCTYPE html>", body)
            self.assertIn("audit dashboard", body)

    def test_root_no_token_returns_401(self):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=2)
            self.fail("expected 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_root_wrong_token_returns_401(self):
        try:
            urllib.request.urlopen(self._url("/", token="wrong"), timeout=2)
            self.fail("expected 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_post_returns_405(self):
        req = urllib.request.Request(self._url("/"), method="POST", data=b"x")
        try:
            urllib.request.urlopen(req, timeout=2)
            self.fail("expected 405")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 405)

    def test_put_returns_405(self):
        req = urllib.request.Request(self._url("/"), method="PUT", data=b"x")
        try:
            urllib.request.urlopen(req, timeout=2)
            self.fail("expected 405")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 405)

    def test_delete_returns_405(self):
        req = urllib.request.Request(self._url("/"), method="DELETE")
        try:
            urllib.request.urlopen(req, timeout=2)
            self.fail("expected 405")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 405)

    def test_unknown_path_returns_404(self):
        try:
            urllib.request.urlopen(self._url("/nope"), timeout=2)
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_cache_control_no_store(self):
        with urllib.request.urlopen(self._url("/"), timeout=2) as r:
            self.assertEqual(r.headers.get("Cache-Control"), "no-store")

    def test_events_stream_replays_tail(self):
        """Use raw socket to read SSE chunks without blocking on full body."""
        import socket
        s = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        s.settimeout(1.5)
        req = (
            f"GET /events?t={self.token} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            "Accept: text/event-stream\r\n"
            "Connection: keep-alive\r\n\r\n"
        )
        s.sendall(req.encode("ascii"))
        received = b""
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and b"veto_triggered" not in received:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                received += chunk
            except socket.timeout:
                break
        s.close()
        self.assertIn(b"200", received)
        self.assertIn(b"text/event-stream", received)
        self.assertIn(b"agent_spawn", received)
        self.assertIn(b"veto_triggered", received)

    def test_loopback_enforced(self):
        rc = audit_dashboard._cli(["--bind", "0.0.0.0"])
        self.assertEqual(rc, 2)

    def test_events_stream_resets_pos_on_rotation(self):
        """When the log file shrinks (rotation), the SSE stream must reset
        its read position to 0 and re-stream new content. This covers the
        `if size < pos: pos = 0` branch in _stream_events()."""
        import socket
        s = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        s.settimeout(1.5)
        req = (
            f"GET /events?t={self.token} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            "Accept: text/event-stream\r\n"
            "Connection: keep-alive\r\n\r\n"
        )
        s.sendall(req.encode("ascii"))

        # Drain the initial tail replay
        received = b""
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and b"veto_triggered" not in received:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                received += chunk
            except socket.timeout:
                break

        # Simulate rotation: truncate log and write a new, shorter marker
        # event. The old `pos` (before truncate) is > current size, so the
        # follow loop MUST detect `size < pos` and reset pos=0.
        time.sleep(0.4)  # let the follow loop settle past the initial replay
        self.log.write_text(
            json.dumps({"ts": "2026-04-12T11:00:00Z", "action": "agent_spawn", "skill": "post_rotation_marker"}) + "\n"
        )

        # Wait for the next poll cycle (follow loop sleeps 0.25s)
        post_rotation = b""
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and b"post_rotation_marker" not in post_rotation:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                post_rotation += chunk
            except socket.timeout:
                continue
        s.close()

        self.assertIn(
            b"post_rotation_marker",
            post_rotation,
            "SSE stream did not re-emit events after log rotation "
            "(pos=0 reset path not reached)",
        )


class StateTest(unittest.TestCase):
    def test_sse_acquire_release_respects_cap(self):
        state = audit_dashboard.DashboardState(
            token="x", log_path=Path("/nonexistent"), tail_n=10, max_connections=2
        )
        self.assertTrue(state.sse_acquire())
        self.assertTrue(state.sse_acquire())
        self.assertFalse(state.sse_acquire())
        state.sse_release()
        self.assertTrue(state.sse_acquire())

    def test_panel_acquire_release_respects_cap(self):
        state = audit_dashboard.DashboardState(
            token="x", log_path=Path("/nonexistent"), tail_n=10,
            max_connections=4, panel_max_clients=2,
        )
        self.assertTrue(state.panel_acquire())
        self.assertTrue(state.panel_acquire())
        self.assertFalse(state.panel_acquire())
        state.panel_release()
        self.assertTrue(state.panel_acquire())


# -----------------------------------------------------------------------------
# PLAN-010 Phase 4: panel tests (debate C12 acceptance)
# -----------------------------------------------------------------------------


class PanelBaseTest(unittest.TestCase):
    """Base fixture: seeds a rich JSONL and starts a fresh server."""

    def _seed_events(self):
        return [
            # agent_spawn with flat token fields
            {"ts": "2026-04-12T10:00:00Z", "action": "agent_spawn",
             "archetype": "staff-backend", "skill": "concurrency",
             "tokens_in": 1000, "tokens_out": 500},
            # agent_spawn with usage.total_tokens shape
            {"ts": "2026-04-12T11:00:00Z", "action": "agent_spawn",
             "archetype": "code-reviewer", "skill": "review",
             "usage": {"total_tokens": 2000}},
            # agent_spawn with no tokens
            {"ts": "2026-04-12T12:00:00Z", "action": "agent_spawn",
             "archetype": "staff-backend", "skill": "misc"},
            # lesson_outcome events
            {"ts": "2026-04-12T10:05:00Z", "action": "lesson_outcome",
             "lesson_id": "lesson-001", "hit": True,
             "inference_mode": "session-correlated", "consumer": "architect"},
            {"ts": "2026-04-12T10:06:00Z", "action": "lesson_outcome",
             "lesson_id": "lesson-001", "hit": False,
             "inference_mode": "session-correlated", "consumer": "architect"},
            {"ts": "2026-04-12T10:07:00Z", "action": "lesson_outcome",
             "lesson_id": "lesson-002", "hit": True,
             "inference_mode": "window-only", "consumer": "benchmark"},
            # lesson_read injection tracking
            {"ts": "2026-04-12T10:08:00Z", "action": "lesson_read",
             "lesson_ids": ["lesson-001", "lesson-003"]},
            # pruning events (recent — within 24h of "now")
            {"ts": self._recent_ts(hours_ago=1), "action": "lesson_archived",
             "lesson_id": "lesson-004"},
            {"ts": self._recent_ts(hours_ago=2), "action": "lesson_archived",
             "lesson_id": "lesson-005",
             "force_dangerous_threshold": True},
            {"ts": self._recent_ts(hours_ago=1), "action": "lesson_restored",
             "lesson_id": "lesson-004"},
        ]

    def _recent_ts(self, hours_ago: int) -> str:
        from datetime import datetime, timezone, timedelta
        return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)) \
            .strftime("%Y-%m-%dT%H:%M:%SZ")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-test-")
        self.log = Path(self.tmp) / "audit-log.jsonl"
        # Restore CEO_AUDIT_LOG_PATH on teardown so this plain TestCase does not
        # leak a stale value into later tests in the sequential scripts pass.
        self.addCleanup(
            lambda _p=os.environ.get("CEO_AUDIT_LOG_PATH"):
            os.environ.__setitem__("CEO_AUDIT_LOG_PATH", _p) if _p is not None
            else os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        )
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log)

        lines = [json.dumps(e) for e in self._seed_events()]
        self.log.write_text("\n".join(lines) + "\n")

        self.token = "panel-token-" + str(os.getpid())
        state = audit_dashboard.DashboardState(
            token=self.token, log_path=self.log, tail_n=10,
            max_connections=4, panel_max_clients=5,
        )
        self.state = state
        handler = audit_dashboard._make_handler(state)
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)

    def _url(self, path: str, token=None):
        t = token if token is not None else self.token
        sep = "&" if "?" in path else "?"
        return f"http://127.0.0.1:{self.port}{path}{sep}t={t}"

    def _assert_auth_fail(self, path: str):
        """Auth regression: unauth → 401. Debate C12 explicit test per panel."""
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=2)
            self.fail(f"expected 401 on {path} without token")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401, f"{path} without token must 401")
        try:
            urllib.request.urlopen(self._url(path, token="wrong-token"), timeout=2)
            self.fail(f"expected 401 on {path} with wrong token")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)


class TokensPanelTest(PanelBaseTest):
    def test_tokens_panel_happy_path(self):
        with urllib.request.urlopen(self._url("/panel/tokens"), timeout=3) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            self.assertIn("Token usage", body)
            # staff-backend total = 1000+500 = 1500 (second spawn had no tokens)
            self.assertIn("staff-backend", body)
            self.assertIn("1,500", body)
            self.assertIn("code-reviewer", body)
            self.assertIn("2,000", body)

    def test_tokens_panel_auth_fail(self):
        self._assert_auth_fail("/panel/tokens")


class ReflexionPanelTest(PanelBaseTest):
    def test_reflexion_panel_happy_path(self):
        with urllib.request.urlopen(self._url("/panel/reflexion"), timeout=3) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            self.assertIn("Reflexion", body)
            self.assertIn("lesson-001", body)
            # 1 hit / 1 miss → 50%
            self.assertIn("50.0%", body)

    def test_reflexion_panel_auth_fail(self):
        self._assert_auth_fail("/panel/reflexion")


class PruningPanelTest(PanelBaseTest):
    def test_pruning_panel_happy_path(self):
        with urllib.request.urlopen(self._url("/panel/pruning"), timeout=3) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            self.assertIn("Pruning", body)
            # safety_guard_triggers = 1 (from force_dangerous_threshold fixture)
            self.assertIn("safety-guard triggers", body)
            # 2 archived in 24h, 1 unique restored → 50%
            self.assertIn("50.0%", body)

    def test_pruning_panel_auth_fail(self):
        self._assert_auth_fail("/panel/pruning")


class ArchitectOutcomesPanelTest(PanelBaseTest):
    def test_architect_outcomes_panel_happy_path(self):
        with urllib.request.urlopen(self._url("/panel/architect-outcomes"), timeout=3) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            self.assertIn("Architect outcomes", body)
            self.assertIn("session-correlated", body)
            self.assertIn("window-only", body)
            self.assertIn("architect", body)
            self.assertIn("benchmark", body)

    def test_architect_outcomes_panel_auth_fail(self):
        self._assert_auth_fail("/panel/architect-outcomes")


# -----------------------------------------------------------------------------
# PLAN-010 Phase 4: edge cases (debate C12 acceptance)
# -----------------------------------------------------------------------------


class PanelEdgeCaseTest(unittest.TestCase):
    """Empty-state, malformed JSONL fail-open, concurrent reader + rotation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-edge-")
        self.log = Path(self.tmp) / "audit-log.jsonl"
        # Restore CEO_AUDIT_LOG_PATH on teardown so this plain TestCase does not
        # leak a stale value into later tests in the sequential scripts pass.
        self.addCleanup(
            lambda _p=os.environ.get("CEO_AUDIT_LOG_PATH"):
            os.environ.__setitem__("CEO_AUDIT_LOG_PATH", _p) if _p is not None
            else os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        )
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log)
        self.token = "edge-token-" + str(os.getpid())

    def _start(self):
        state = audit_dashboard.DashboardState(
            token=self.token, log_path=self.log, tail_n=10,
            max_connections=4, panel_max_clients=5,
        )
        handler = audit_dashboard._make_handler(state)
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.thread.join(timeout=2)

    def _url(self, path):
        sep = "&" if "?" in path else "?"
        return f"http://127.0.0.1:{self.port}{path}{sep}t={self.token}"

    def test_empty_log_returns_empty_state_html_not_error(self):
        """Debate C12: Panel with 0 events returns empty-state HTML (not error)."""
        self.log.write_text("")  # empty file
        self._start()
        for panel in ("/panel/tokens", "/panel/reflexion",
                      "/panel/pruning", "/panel/architect-outcomes"):
            with urllib.request.urlopen(self._url(panel), timeout=3) as r:
                self.assertEqual(r.status, 200, f"{panel} should return 200 on empty log")
                body = r.read().decode("utf-8")
                self.assertIn("<!DOCTYPE html>", body)
                # Either a "no … yet" empty state or zero totals — never 500
                self.assertTrue(
                    ("empty" in body.lower() or "0" in body),
                    f"{panel} empty state missing marker",
                )

    def test_malformed_jsonl_line_skipped_fail_open(self):
        """Debate C12: malformed JSONL line → skip + warn + continue."""
        self.log.write_text(
            json.dumps({"ts": "2026-04-12T10:00:00Z", "action": "agent_spawn",
                        "archetype": "staff", "tokens_in": 100, "tokens_out": 50}) + "\n"
            "{not valid json at all\n"
            + json.dumps({"ts": "2026-04-12T10:01:00Z", "action": "agent_spawn",
                          "archetype": "staff", "tokens_in": 200, "tokens_out": 100}) + "\n"
        )
        self._start()
        with urllib.request.urlopen(self._url("/panel/tokens"), timeout=3) as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode("utf-8")
            # Both valid events aggregated: 100+50+200+100 = 450
            self.assertIn("450", body)

    def test_concurrent_reader_during_rotation(self):
        """Debate C12: fixture — write events → trigger rotation → reader reads both halves.

        We open the first panel request, then rotate the log (truncate +
        write new content), then open a second panel request. Both must
        succeed and reflect their respective snapshots.
        """
        self.log.write_text(
            json.dumps({"ts": "2026-04-12T10:00:00Z", "action": "agent_spawn",
                        "archetype": "first-half", "tokens_in": 100, "tokens_out": 0}) + "\n"
        )
        self._start()

        # First read — should see "first-half"
        with urllib.request.urlopen(self._url("/panel/tokens"), timeout=3) as r:
            body1 = r.read().decode("utf-8")
        self.assertIn("first-half", body1)

        # Rotate: truncate + write a new event set
        self.log.write_text(
            json.dumps({"ts": "2026-04-12T11:00:00Z", "action": "agent_spawn",
                        "archetype": "second-half", "tokens_in": 200, "tokens_out": 0}) + "\n"
        )

        # Second read — should see "second-half" (and NOT first-half)
        with urllib.request.urlopen(self._url("/panel/tokens"), timeout=3) as r:
            body2 = r.read().decode("utf-8")
        self.assertIn("second-half", body2)
        # first-half was truncated, so its row should not appear
        self.assertNotIn("first-half", body2)

    def test_panel_max_clients_cap_rejects_overflow(self):
        """Debate C12: Max 5 concurrent clients (reject 6th with 503)."""
        self.log.write_text("")
        state = audit_dashboard.DashboardState(
            token=self.token, log_path=self.log, tail_n=10,
            max_connections=4, panel_max_clients=2,
        )
        handler = audit_dashboard._make_handler(state)
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

        # Exhaust the panel slot pool manually, then issue a request
        self.assertTrue(state.panel_acquire())
        self.assertTrue(state.panel_acquire())
        try:
            urllib.request.urlopen(self._url("/panel/tokens"), timeout=2)
            self.fail("expected 503 when panel cap is reached")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 503)
        state.panel_release()
        state.panel_release()

    def test_socket_timeout_is_set(self):
        """Debate C12: per-connection timeout ≤30s server-side."""
        self.assertLessEqual(audit_dashboard.PANEL_REQUEST_TIMEOUT_S, 30)
        self.assertGreater(audit_dashboard.PANEL_REQUEST_TIMEOUT_S, 0)


# -----------------------------------------------------------------------------
# Pure aggregation unit tests (no HTTP)
# -----------------------------------------------------------------------------


class AggregationUnitTest(unittest.TestCase):
    def test_aggregate_tokens_prefers_usage_then_flat(self):
        events = [
            {"action": "agent_spawn", "ts": "2026-04-12T00:00:00Z",
             "archetype": "a", "usage": {"total_tokens": 500}},
            {"action": "agent_spawn", "ts": "2026-04-12T00:00:00Z",
             "archetype": "a", "tokens_in": 100, "tokens_out": 50},
            {"action": "agent_spawn", "ts": "2026-04-12T00:00:00Z",
             "archetype": "b"},
            {"action": "veto_triggered"},  # non-spawn ignored
        ]
        agg = audit_dashboard.aggregate_tokens(events)
        totals = {r["archetype"]: r["total_tokens"] for r in agg["per_archetype_total"]}
        self.assertEqual(totals["a"], 650)
        self.assertEqual(agg["records_without_tokens"], 1)
        self.assertEqual(agg["spawn_count"], 3)

    def test_aggregate_reflexion_excludes_window_only_by_default(self):
        events = [
            {"action": "lesson_outcome", "lesson_id": "L1", "hit": True,
             "inference_mode": "session-correlated"},
            {"action": "lesson_outcome", "lesson_id": "L1", "hit": True,
             "inference_mode": "window-only"},  # excluded
        ]
        agg = audit_dashboard.aggregate_reflexion(events)
        self.assertEqual(agg["global_hit"], 1)
        self.assertEqual(agg["global_miss"], 0)

    def test_aggregate_pruning_windows(self):
        from datetime import datetime, timezone, timedelta
        now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # In 24h window
            {"action": "lesson_archived", "ts": "2026-04-14T10:00:00Z",
             "lesson_id": "L1"},
            {"action": "lesson_restored", "ts": "2026-04-14T11:00:00Z",
             "lesson_id": "L1"},
            # 7d window only
            {"action": "lesson_archived", "ts": "2026-04-10T10:00:00Z",
             "lesson_id": "L2", "force_dangerous_threshold": True},
        ]
        agg = audit_dashboard.aggregate_pruning(events, now=now)
        self.assertEqual(agg["windows"]["24h"]["archived_count"], 1)
        self.assertEqual(agg["windows"]["24h"]["unique_restored"], 1)
        self.assertEqual(agg["windows"]["7d"]["archived_count"], 2)
        self.assertEqual(agg["safety_guard_triggers"], 1)

    def test_aggregate_architect_outcomes_breakdown(self):
        events = [
            {"action": "lesson_outcome", "hit": True,
             "inference_mode": "session-correlated", "consumer": "architect"},
            {"action": "lesson_outcome", "hit": False,
             "inference_mode": "window-only", "consumer": "benchmark"},
            {"action": "lesson_outcome", "hit": True,
             "inference_mode": "session-correlated", "consumer": "architect"},
        ]
        agg = audit_dashboard.aggregate_architect_outcomes(events)
        self.assertEqual(agg["total_outcomes"], 3)
        self.assertEqual(agg["by_inference_mode"]["session-correlated"], 2)
        self.assertEqual(agg["by_inference_mode"]["window-only"], 1)
        architect_row = [r for r in agg["by_consumer"] if r["consumer"] == "architect"][0]
        self.assertEqual(architect_row["hits"], 2)
        self.assertEqual(architect_row["misses"], 0)
        self.assertEqual(architect_row["effectiveness"], 1.0)


class TestBoundedReverseScan(unittest.TestCase):
    """Perf-P1-003 — ``_tail_lines_reverse`` bounded-memory tail.

    Exercises the reverse-scan directly as a function, since the SSE
    handler wraps it as ``_read_tail``.  These tests cover the full
    contract surface: small logs, exact boundary, multi-chunk scans,
    empty lines, trailing newline vs not, unicode-safe decode,
    missing file, n<=0, and the memory ceiling on a 50 MB file.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dash-tail-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, content):
        p = self.tmp / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_missing_file_returns_empty(self):
        missing = self.tmp / "nope.jsonl"
        self.assertEqual(audit_dashboard._tail_lines_reverse(missing, 10), [])

    def test_n_zero_or_negative_returns_empty(self):
        p = self._write("log.jsonl", "a\nb\nc\n")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 0), [])
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, -5), [])

    def test_empty_file_returns_empty(self):
        p = self._write("log.jsonl", "")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 10), [])

    def test_small_log_returns_all_lines(self):
        p = self._write("log.jsonl", "a\nb\nc\n")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 10), ["a", "b", "c"])

    def test_small_log_returns_last_n(self):
        p = self._write("log.jsonl", "a\nb\nc\nd\ne\n")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 2), ["d", "e"])

    def test_blank_lines_excluded(self):
        p = self._write("log.jsonl", "a\n\nb\n  \nc\n")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 10), ["a", "b", "c"])

    def test_no_trailing_newline(self):
        p = self._write("log.jsonl", "a\nb\nc")
        self.assertEqual(audit_dashboard._tail_lines_reverse(p, 10), ["a", "b", "c"])

    def test_unicode_content_round_trip(self):
        # Keep it ASCII-safe for test robustness, but ensure bytes≠chars
        # lines are decoded cleanly.
        p = self._write("log.jsonl", "alpha\nbeta \u00e9vt\ngamma\n")
        result = audit_dashboard._tail_lines_reverse(p, 10)
        self.assertEqual(result, ["alpha", "beta \u00e9vt", "gamma"])

    def test_multichunk_scan_boundary(self):
        """Force many chunks to trigger backward chunked reads."""
        # Each line ~50 bytes; 10_000 lines ~ 500 KB ≫ single 64 KiB chunk.
        lines = [
            f'{{"ts":"2026-04-01T00:00:{i:02d}Z","i":{i}}}' for i in range(10_000)
        ]
        p = self._write("log.jsonl", "\n".join(lines) + "\n")
        result = audit_dashboard._tail_lines_reverse(p, 100)
        self.assertEqual(len(result), 100)
        # Last line in result must be the last logical record.
        self.assertIn('"i":9999', result[-1])
        self.assertIn('"i":9900', result[0])

    def test_parity_with_prior_read_text_splitlines(self):
        """Contract: for any file fitting in RAM, the returned lines
        must exactly match ``log.read_text().splitlines()[-n:]`` after
        blank-line filtering — the pre-Perf-P1-003 behaviour."""
        content = "alpha\nbeta\ngamma\ndelta\nepsilon\n"
        p = self._write("log.jsonl", content)
        lines = [l for l in content.splitlines() if l.strip()]
        for n in (1, 2, 3, 4, 5, 6, 100):
            expected = lines[-n:] if n > 0 else []
            self.assertEqual(
                audit_dashboard._tail_lines_reverse(p, n),
                expected,
                f"parity broke at n={n}",
            )

    def test_memory_footprint_on_50mb_log(self):
        """Perf-P1-003 acceptance: 50 MB log → <5 MB resident growth.

        Uses ``tracemalloc`` (stdlib) to measure peak *Python* heap
        growth during the reverse-scan. That is the correct proxy for
        "does this code allocate the whole file?" — a full-materialize
        would blow past 50 MB peak; the bounded scan caps at a handful
        of hundred KB (64 KiB chunk + n lines).
        """
        import tracemalloc
        # Build a ~50 MB log: ~800-byte lines × 65_000 ≈ 52 MB.
        line = (
            '{"ts":"2026-04-01T12:00:00Z","action":"agent_spawn",'
            '"skill":"example","has_profile":true,'
            '"has_file_assignment":true,"desc_preview":"'
            + ("x" * 700) + '"}\n'
        )
        p = self.tmp / "big.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for _ in range(65_000):
                f.write(line)
        size = p.stat().st_size
        self.assertGreaterEqual(
            size, 50 * 1024 * 1024,
            f"fixture must be >=50 MB (got {size} bytes)",
        )

        tracemalloc.start()
        result = audit_dashboard._tail_lines_reverse(p, 1000)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertEqual(len(result), 1000)
        # Budget: <5 MB = 5 * 1024 * 1024 bytes.
        self.assertLess(
            peak,
            5 * 1024 * 1024,
            f"bounded reverse-scan allocated {peak/1024/1024:.1f} MB "
            f"peak on 50 MB log; budget is 5 MB",
        )


class TestSSEMemoryFootprint(unittest.TestCase):
    """Perf-P1-003 — end-to-end SSE connect memory test.

    Smoke-test the _read_tail integration via the handler class (which
    delegates to _tail_lines_reverse). We don't actually open an SSE
    connection in this test — the key correctness + memory behaviour
    is in the helper, and the handler integration is covered by the
    existing dashboard tests that start a real server.
    """

    def test_read_tail_uses_reverse_scan_helper(self):
        """The handler's ``_read_tail`` must route through the bounded-
        scan helper, not the old ``read_text().splitlines()`` path.

        Proof-by-replacement: monkey-patch ``_tail_lines_reverse`` to a
        sentinel value; the handler's _read_tail must return the
        sentinel, proving it uses the helper.
        """
        tmp = tempfile.mkdtemp(prefix="dash-stub-")
        try:
            log = Path(tmp) / "audit-log.jsonl"
            log.write_text("a\nb\nc\n")
            state = audit_dashboard.DashboardState(
                token="tok", log_path=log, tail_n=3, max_connections=4,
            )
            HandlerCls = audit_dashboard._make_handler(state)

            original = audit_dashboard._tail_lines_reverse
            sentinel = ["REVERSE-SCAN-ROUTED-HERE"]
            audit_dashboard._tail_lines_reverse = lambda *_a, **_k: sentinel
            try:
                # Instantiate the handler without binding to a socket by
                # calling _read_tail as an unbound method — but _read_tail
                # is bound to a request instance. We instead create a
                # lightweight stand-in that has _read_tail and invoke it.
                class _Stub:
                    _read_tail = HandlerCls._read_tail
                stub = _Stub()
                out = stub._read_tail(log, 3)
                self.assertEqual(out, sentinel)
            finally:
                audit_dashboard._tail_lines_reverse = original
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class SSEBackoffTest(unittest.TestCase):
    """PLAN-019 Perf-P2-003 — SSE loop uses exponential backoff.

    The prior implementation had a hard-coded ``time.sleep(0.25)`` busy-loop.
    The fix uses ``POLL_MIN`` (0.1s) on active bursts and grows to
    ``POLL_MAX`` (2.0s) on idle.

    These are grey-box tests: we assert the source file contains the
    updated constants + the adaptive logic. A live end-to-end test that
    measured sleep() calls under load would be too flaky for CI.
    """

    def setUp(self):
        from pathlib import Path as _P
        self.source = (
            _P(audit_dashboard.__file__).read_text(encoding="utf-8")
        )

    def test_poll_min_constant_present(self):
        # The inner SSE loop references POLL_MIN = 0.1 (seconds).
        self.assertIn("POLL_MIN = 0.1", self.source)

    def test_poll_max_constant_present(self):
        # Cap is 2.0s per DevOps+Perf skill rule (idle CPU bound).
        self.assertIn("POLL_MAX = 2.0", self.source)

    def test_adaptive_wait_doubles_on_idle(self):
        # The backoff is implemented as `wait = min(POLL_MAX, wait * 2)`.
        self.assertIn("wait = min(POLL_MAX, wait * 2)", self.source)

    def test_wait_resets_on_new_bytes(self):
        # On fresh data, reset wait to POLL_MIN so first-byte latency is low.
        self.assertIn("wait = POLL_MIN", self.source)

    def test_fixed_250ms_sleep_removed(self):
        # Regression: the old fixed polling interval must be gone.
        # The busy-stat loop previously used time.sleep(0.25).
        self.assertNotIn("time.sleep(0.25)", self.source)


if __name__ == "__main__":
    unittest.main()
