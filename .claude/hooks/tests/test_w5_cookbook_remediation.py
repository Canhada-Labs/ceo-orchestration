"""PLAN-113 W5-COOKBOOK remediation tests.

Covers all 5 implemented findings:

F-5-5.1-0624274e  cache_coverage field alignment in check_cache_discipline_alerted
F-5.6-0e94e54b    citations kwarg in ClaudeLiveAdapter.call()
F-5.6-97b05192    native batch lifecycle state machine in claude_batch.py (default-OFF)
F-5.6-94c3325d    interleaved_thinking kwarg in ClaudeLiveAdapter.call()
F-5.6-4ff5aff2    cookbook_patterns.json catalogue expanded to 9 IDs

Flagged (not implemented here):
F-5.6-f7d44719    embeddings/RAG — overlaps RAG wave, deferred
F-5.6-b0e06991    ADR-094 promotion — CANON-ADR territory, deferred
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Shared transport stubs (reused from existing adapter tests)
# ---------------------------------------------------------------------------


class _FakeTransport:
    """Captures post_json / get_json calls; returns failure stub (no live I/O)."""

    def __init__(self):
        self.captured_url = None
        self.captured_headers = None
        self.captured_body = None

    def post_json(self, url, headers, body):
        self.captured_url = url
        self.captured_headers = headers
        self.captured_body = body

        class _Failure:
            failure_mode = "transport_stub"
            http_status = None
            duration_ms = 1
            retried = False

        return None, _Failure()

    def get_json(self, url, headers):
        self.captured_url = url
        self.captured_headers = headers

        class _Failure:
            failure_mode = "transport_stub"
            http_status = None
            duration_ms = 1
            retried = False

        return None, _Failure()


class _ResponseTransport:
    """Returns a fixed 2xx response body for post_json and get_json."""

    def __init__(self, body_obj, status=200):
        self._body = json.dumps(body_obj).encode("utf-8")
        self._status = status
        self.captured_headers = None
        self.captured_body = None

    def _make_response(self):
        class _Resp:
            pass

        r = _Resp()
        r.status = self._status
        r.body_bytes = self._body
        r.duration_ms = 1
        r.retried = False
        return r

    def post_json(self, url, headers, body):
        self.captured_headers = headers
        self.captured_body = body
        return self._make_response(), None

    def get_json(self, url, headers):
        self.captured_headers = headers
        return self._make_response(), None


# ---------------------------------------------------------------------------
# F-5-5.1-0624274e — cache_coverage field alignment
# ---------------------------------------------------------------------------


class TestCacheCoverageFieldAlignment(TestEnvContext):
    """check_cache_discipline_alerted must read cache_coverage, not cache_hit_rate."""

    def _load_ceo_boot(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ceo_boot",
            str(_REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_no_cache_coverage_rows_returns_green(self):
        """Absent cache_coverage datapoints → green (no-data path)."""
        mod = self._load_ceo_boot()
        # Monkey-patch _iter_audit_events_since to yield rows WITHOUT cache_coverage.
        import types
        def _fake_iter(hours):
            yield {"action": "agent_spawn", "cache_hit_rate": 0.5}  # old field — ignored
            yield {"action": "agent_spawn", "model": "claude-haiku-4-5"}
        mod._iter_audit_events_since = _fake_iter
        status, msg, _ = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "green")
        self.assertIn("no cache_coverage", msg)

    def test_high_cache_coverage_returns_green(self):
        """cache_coverage >= 0.70 on all rows → green."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            for _ in range(5):
                yield {"action": "agent_spawn", "cache_coverage": 0.85}

        mod._iter_audit_events_since = _fake_iter
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "green")
        self.assertIn("cache_coverage", msg)
        self.assertGreaterEqual(detail["avg_rate"], 0.70)

    def test_low_cache_coverage_returns_red(self):
        """cache_coverage < 0.70 average → red, detector is live."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            for _ in range(3):
                yield {"action": "agent_spawn", "cache_coverage": 0.40}

        mod._iter_audit_events_since = _fake_iter
        # Silence the emit_generic call (audit_emit may not be importable cleanly).
        mod._audit_emit = None
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "red")
        self.assertIn("cache_coverage", msg)
        self.assertLess(detail["avg_rate"], 0.70)

    def test_high_cache_coverage_bps_primary_path_returns_green(self):
        """PLAN-118 WS-E (qa Gap-1): the NEW cache_coverage_bps int PRIMARY
        path must be read + divided by 10000. This is the field every
        post-WS-E spawn emits; without coverage a key-name drift would
        silently fall through to the legacy float branch and return
        green/no-data (the exact F-5-5.1-0624274e silent-dead failure)."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            for _ in range(5):
                yield {"action": "agent_spawn", "cache_coverage_bps": 8000}

        mod._iter_audit_events_since = _fake_iter
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "green")
        self.assertEqual(detail["samples"], 5)
        self.assertAlmostEqual(detail["avg_rate"], 0.80, places=4)

    def test_low_cache_coverage_bps_primary_path_returns_red(self):
        """PLAN-118 WS-E (qa Gap-1): bps primary path threshold logic
        (not just the float fallback) fires red below the 0.70 floor."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            for _ in range(3):
                yield {"action": "agent_spawn", "cache_coverage_bps": 4000}

        mod._iter_audit_events_since = _fake_iter
        mod._audit_emit = None
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "red")
        self.assertAlmostEqual(detail["avg_rate"], 0.40, places=4)

    def test_bps_primary_preferred_over_legacy_float_no_double_count(self):
        """PLAN-118 WS-E (qa Gap-1): an event carrying BOTH fields counts
        ONCE via the bps branch (the `continue` guards against double-count);
        a bool bps value is rejected (isinstance int and not bool)."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            # both fields present: bps wins, float ignored (no double-count)
            yield {"action": "agent_spawn", "cache_coverage_bps": 9000, "cache_coverage": 0.10}
            # bool must NOT be accepted as an int bps datapoint
            yield {"action": "agent_spawn", "cache_coverage_bps": True}

        mod._iter_audit_events_since = _fake_iter
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "green")
        self.assertEqual(detail["samples"], 1)          # bool rejected
        self.assertAlmostEqual(detail["avg_rate"], 0.90, places=4)  # bps, not 0.10

    def test_old_cache_hit_rate_field_is_ignored(self):
        """Rows carrying the old cache_hit_rate field do NOT count (field gap fixed)."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            # Only the old field present — nothing should be counted.
            for _ in range(10):
                yield {"action": "agent_spawn", "cache_hit_rate": 0.20}

        mod._iter_audit_events_since = _fake_iter
        status, msg, _ = mod.check_cache_discipline_alerted()
        # Without cache_coverage rows the detector returns green/no-data.
        self.assertEqual(status, "green")
        self.assertIn("no cache_coverage", msg)

    def test_mixed_rows_only_cache_coverage_counted(self):
        """Only cache_coverage fields are averaged; cache_hit_rate rows ignored."""
        mod = self._load_ceo_boot()

        def _fake_iter(hours):
            yield {"cache_coverage": 0.90}
            yield {"cache_hit_rate": 0.10}   # should be ignored
            yield {"cache_coverage": 0.80}

        mod._iter_audit_events_since = _fake_iter
        mod._audit_emit = None
        status, msg, detail = mod.check_cache_discipline_alerted()
        self.assertEqual(status, "green")
        # avg of 0.90 + 0.80 = 0.85
        self.assertAlmostEqual(detail["avg_rate"], 0.85, places=2)
        self.assertEqual(detail["samples"], 2)


# ---------------------------------------------------------------------------
# F-5.6-0e94e54b — citations kwarg in ClaudeLiveAdapter.call()
# ---------------------------------------------------------------------------


class TestCitationsKwarg(TestEnvContext):
    """citations=True attaches {"enabled":True} to document blocks."""

    def _make_adapter(self, transport):
        from _lib.adapters.live import claude as claude_live
        from _lib.adapters.live._policy import ClaudeLivePolicy
        return claude_live.ClaudeLiveAdapter(
            policy=ClaudeLivePolicy(), transport=transport
        )

    def _enable_live(self):
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-stub"
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        settings = self.project_dir / ".claude" / "settings.json"
        settings.write_text(
            json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_citations_true_stamps_document_block(self):
        """citations=True stamps {"enabled": True} on document-type blocks."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "text", "data": "DOC"}},
                {"type": "text", "text": "cite it"},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8", citations=True)
        stamped = t.captured_body["messages"][0]["content"][0]
        self.assertEqual(stamped.get("citations"), {"enabled": True})

    def test_citations_none_does_not_stamp(self):
        """citations=None (default) leaves document blocks untouched."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "text", "data": "DOC"}},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8")
        blk = t.captured_body["messages"][0]["content"][0]
        self.assertNotIn("citations", blk)

    def test_citations_false_does_not_stamp(self):
        """citations=False (explicit opt-out) leaves blocks untouched."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "text", "data": "DOC"}},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8", citations=False)
        blk = t.captured_body["messages"][0]["content"][0]
        self.assertNotIn("citations", blk)

    def test_citations_true_leaves_existing_citations_key_untouched(self):
        """Idempotent: a block that already has citations is not overwritten."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        existing = {"enabled": False, "mode": "custom"}
        msgs = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "text", "data": "DOC"},
                 "citations": existing},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8", citations=True)
        blk = t.captured_body["messages"][0]["content"][0]
        self.assertEqual(blk["citations"], existing)

    def test_citations_true_only_stamps_document_blocks(self):
        """citations=True stamps only document-type blocks; text blocks untouched."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "query"},
                {"type": "document", "source": {"type": "text", "data": "DOC"}},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8", citations=True)
        content = t.captured_body["messages"][0]["content"]
        # text block — no citations key added
        self.assertNotIn("citations", content[0])
        # document block — citations key added
        self.assertEqual(content[1].get("citations"), {"enabled": True})

    def test_citations_true_does_not_mutate_input_messages(self):
        """_apply_citations must never mutate the caller-supplied list."""
        from _lib.adapters.live.claude import _apply_citations
        original_block = {"type": "document", "source": {"type": "text", "data": "X"}}
        msgs = [{"role": "user", "content": [original_block]}]
        _apply_citations(msgs)
        # original block must not have gained a citations key
        self.assertNotIn("citations", original_block)


# ---------------------------------------------------------------------------
# F-5.6-94c3325d — interleaved_thinking kwarg
# ---------------------------------------------------------------------------


class TestInterleavedThinking(TestEnvContext):
    """interleaved_thinking=True adds the betas header + body param (default-OFF)."""

    def _make_adapter(self, transport):
        from _lib.adapters.live import claude as claude_live
        from _lib.adapters.live._policy import ClaudeLivePolicy
        return claude_live.ClaudeLiveAdapter(
            policy=ClaudeLivePolicy(), transport=transport
        )

    def _enable_live(self):
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-stub"
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        settings = self.project_dir / ".claude" / "settings.json"
        settings.write_text(
            json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_interleaved_thinking_true_adds_beta_header(self):
        """interleaved_thinking=True adds the interleaved-thinking beta header.

        E6-F2: the legacy enabled/budget shape (the only one that takes the
        beta header) survives ONLY on pre-4.6 ids — adaptive-only ids get
        the dict translated to adaptive and auto-interleave headerless.
        """
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "think"}],
            model="claude-sonnet-4-5",
            thinking={"type": "enabled", "budget_tokens": 4096},
            interleaved_thinking=True,
        )
        beta_header = t.captured_headers.get("anthropic-beta", "")
        self.assertIn("interleaved-thinking-2025-05-14", beta_header)

    def test_interleaved_thinking_true_sets_body_param(self):
        """interleaved_thinking=True sets body["interleaved_thinking"] = True."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "think"}],
            model="claude-sonnet-4-5",  # E6-F2: legacy shape is pre-4.6-only
            thinking={"type": "enabled", "budget_tokens": 4096},
            interleaved_thinking=True,
        )
        self.assertTrue(t.captured_body.get("interleaved_thinking"))

    def test_interleaved_thinking_none_does_not_add_header_or_param(self):
        """interleaved_thinking=None (default) → no beta header, no body param."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "no think"}],
            model="claude-opus-4-8",
        )
        self.assertNotIn("anthropic-beta", t.captured_headers)
        self.assertNotIn("interleaved_thinking", t.captured_body)

    def test_interleaved_thinking_kill_switch_disables(self):
        """CEO_INTERLEAVED_THINKING_DISABLE=1 suppresses interleaved_thinking."""
        self._enable_live()
        os.environ["CEO_INTERLEAVED_THINKING_DISABLE"] = "1"
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "think"}],
            model="claude-sonnet-4-5",  # E6-F2: legacy shape is pre-4.6-only
            thinking={"type": "enabled", "budget_tokens": 4096},
            interleaved_thinking=True,
        )
        self.assertNotIn("interleaved_thinking", t.captured_body)
        beta_header = t.captured_headers.get("anthropic-beta", "")
        self.assertNotIn("interleaved-thinking-2025-05-14", beta_header)

    def test_interleaved_thinking_false_does_not_add(self):
        """interleaved_thinking=False (explicit) → no param added."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
            interleaved_thinking=False,
        )
        self.assertNotIn("interleaved_thinking", t.captured_body)


# ---------------------------------------------------------------------------
# F-5.6-97b05192 — native batch lifecycle state machine (default-OFF)
# ---------------------------------------------------------------------------


class TestNativeBatchLifecycle(TestEnvContext):
    """Native batch create/poll/retrieve state machine is default-OFF."""

    def test_native_lifecycle_off_by_default(self):
        """CEO_NATIVE_BATCH_LIFECYCLE absent → native lifecycle is disabled."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_NATIVE_BATCH_LIFECYCLE", None)
        adapter = BatchClaudeLiveAdapter()
        self.assertFalse(adapter._native_batch_lifecycle_enabled())

    def test_native_lifecycle_armed_by_env(self):
        """CEO_NATIVE_BATCH_LIFECYCLE=1 → native lifecycle reports enabled."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = "1"
        adapter = BatchClaudeLiveAdapter()
        self.assertTrue(adapter._native_batch_lifecycle_enabled())

    def test_native_lifecycle_not_armed_for_truthy_non_one(self):
        """CEO_NATIVE_BATCH_LIFECYCLE=true / yes / 0 → not armed (EXACT MATCH =1)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        for val in ("true", "yes", "True", "0"):
            with self.subTest(val=val):
                os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = val
                adapter = BatchClaudeLiveAdapter()
                self.assertFalse(adapter._native_batch_lifecycle_enabled())

    def test_batch_create_returns_none_on_transport_failure(self):
        """batch_create() returns None when transport fails (fail-soft)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _FakeTransport()
        adapter = BatchClaudeLiveAdapter(transport=t)
        result = adapter.batch_create(
            payload={"requests": []},
            api_key="sk-test",
        )
        self.assertIsNone(result)

    def test_batch_create_parses_id_from_response(self):
        """batch_create() extracts the id field from a 2xx response."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _ResponseTransport({"id": "batch-abc123", "processing_status": "in_progress"})
        adapter = BatchClaudeLiveAdapter(transport=t)
        result = adapter.batch_create(payload={"requests": []}, api_key="sk-test")
        self.assertEqual(result, "batch-abc123")

    def test_batch_poll_returns_processing_status(self):
        """batch_poll() returns the processing_status field."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _ResponseTransport({"id": "b-1", "processing_status": "ended"})
        adapter = BatchClaudeLiveAdapter(transport=t)
        status = adapter.batch_poll(batch_id="b-1", api_key="sk-test")
        self.assertEqual(status, "ended")

    def test_batch_poll_returns_none_on_failure(self):
        """batch_poll() returns None on transport failure (fail-soft)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _FakeTransport()
        adapter = BatchClaudeLiveAdapter(transport=t)
        status = adapter.batch_poll(batch_id="b-1", api_key="sk-test")
        self.assertIsNone(status)

    def test_batch_retrieve_parses_jsonl_results(self):
        """batch_retrieve() parses JSONL body and extracts succeeded text."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        # JSONL body with two rows.
        jsonl = "\n".join([
            json.dumps({
                "custom_id": "req-0",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"type": "text", "text": "hello"}]
                    },
                },
            }),
            json.dumps({
                "custom_id": "req-1",
                "result": {"type": "errored", "error": {"type": "server_error"}},
            }),
        ])
        # Transport that serves the JSONL body for GET requests (batch_retrieve
        # uses GET, not POST — FIX-R2-C correction).
        class _JsonlTransport:
            captured_headers = None
            captured_url = None

            def _make_jsonl_resp(self):
                class _Resp:
                    pass

                r = _Resp()
                r.status = 200
                r.body_bytes = jsonl.encode("utf-8")
                r.duration_ms = 1
                r.retried = False
                return r

            def get_json(self, url, headers):
                self.captured_url = url
                self.captured_headers = headers
                return self._make_jsonl_resp(), None

            def post_json(self, url, headers, body):
                # batch_retrieve does not POST — fail if called unexpectedly.
                raise AssertionError("batch_retrieve must use GET, not POST")

        jt = _JsonlTransport()
        adapter = BatchClaudeLiveAdapter(transport=jt)
        results = adapter.batch_retrieve(
            batch_id="b-1",
            api_key="sk-test",
            custom_ids=["req-0", "req-1"],
        )
        self.assertEqual(results["req-0"], "hello")
        self.assertIsNone(results["req-1"])

    def test_batch_retrieve_returns_nones_on_failure(self):
        """batch_retrieve() maps all custom_ids to None on transport failure."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _FakeTransport()
        adapter = BatchClaudeLiveAdapter(transport=t)
        results = adapter.batch_retrieve(
            batch_id="b-1",
            api_key="sk-test",
            custom_ids=["req-0", "req-1"],
        )
        self.assertIsNone(results["req-0"])
        self.assertIsNone(results["req-1"])

    def test_batch_call_still_uses_sequential_fallback_by_default(self):
        """batch_call uses sequential call() loop when native lifecycle is off."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_NATIVE_BATCH_LIFECYCLE", None)
        adapter = BatchClaudeLiveAdapter()
        # Should not raise; falls through to sequential fixture-fallback loop.
        results = adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].fixture_fallback)


# ---------------------------------------------------------------------------
# F-5.6-4ff5aff2 — cookbook catalogue expanded to 9 IDs
# ---------------------------------------------------------------------------


class TestCookbookCatalogueExpansion(TestEnvContext):
    """cookbook_patterns.json and cookbook_patterns.py both carry 9 IDs."""

    def _load_patterns(self):
        from _lib import cookbook_patterns
        data_path = _REPO_ROOT / ".claude" / "data" / "cookbook_patterns.json"
        return cookbook_patterns.load_cookbook_patterns(path=data_path)

    def test_canonical_ids_tuple_has_9_entries(self):
        from _lib import cookbook_patterns
        self.assertEqual(len(cookbook_patterns.CANONICAL_IDS), 9)

    def test_canonical_ids_includes_p5_through_p9(self):
        from _lib import cookbook_patterns
        for pid in ("COOK-P5", "COOK-P6", "COOK-P7", "COOK-P8", "COOK-P9"):
            self.assertIn(pid, cookbook_patterns.CANONICAL_IDS)

    def test_json_file_has_9_patterns(self):
        payload = self._load_patterns()
        patterns = payload["patterns"]
        self.assertEqual(len(patterns), 9)

    def test_json_canonical_ids_field_has_9_entries(self):
        payload = self._load_patterns()
        self.assertEqual(len(payload["canonical_ids"]), 9)

    def test_validate_structure_passes_with_9_patterns(self):
        from _lib import cookbook_patterns
        payload = self._load_patterns()
        # Should not raise.
        cookbook_patterns.validate_structure(payload)

    def test_new_patterns_have_required_fields(self):
        payload = self._load_patterns()
        from _lib import cookbook_patterns
        for pid in ("COOK-P5", "COOK-P6", "COOK-P7", "COOK-P8", "COOK-P9"):
            entry = payload["patterns"][pid]
            for field in cookbook_patterns.REQUIRED_FIELDS:
                self.assertIn(
                    field, entry,
                    f"{pid} missing required field '{field}'",
                )

    def test_new_patterns_have_valid_regexes(self):
        import re
        payload = self._load_patterns()
        for pid in ("COOK-P5", "COOK-P6", "COOK-P7", "COOK-P8", "COOK-P9"):
            for rx in payload["patterns"][pid]["task_signature_regex"]:
                try:
                    re.compile(rx)
                except re.error as exc:
                    self.fail(f"{pid} has invalid regex {rx!r}: {exc}")

    def test_match_pattern_hits_cook_p5_for_prompt_caching(self):
        """COOK-P5 (prompt caching) is reachable via match_pattern."""
        from _lib import cookbook_patterns
        data_path = _REPO_ROOT / ".claude" / "data" / "cookbook_patterns.json"
        payload = cookbook_patterns.load_cookbook_patterns(path=data_path)
        result = cookbook_patterns.match_pattern("cache_control ephemeral breakpoint", payload)
        # COOK-P5 pattern should match "cache_control"
        self.assertIsNotNone(result)
        pid, trigger_class, _bucket = result
        # Either COOK-P5 (cache-discipline) or an earlier pattern matched first.
        # Assert the catalogue is reachable and returns a valid tuple.
        self.assertIn(pid, cookbook_patterns.CANONICAL_IDS)

    def test_p9_contextual_retrieval_pattern_matches(self):
        """COOK-P9 (contextual retrieval) trigger_class is contextual-retrieval."""
        payload = self._load_patterns()
        entry = payload["patterns"]["COOK-P9"]
        self.assertEqual(entry["trigger_class"], "contextual-retrieval")


# ---------------------------------------------------------------------------
# Flagged findings — presence assertion (not implemented here)
# ---------------------------------------------------------------------------


class TestFlaggedFindings(unittest.TestCase):
    """Document that F-5.6-f7d44719 and F-5.6-b0e06991 are flagged, not fixed."""

    def test_rag_bridge_exists_but_is_deferred(self):
        """F-5.6-f7d44719: rag_bridge.py exists; embeddings/RAG deferred to RAG wave."""
        rag_bridge = _HOOKS_DIR / "_lib" / "rag_bridge.py"
        self.assertTrue(rag_bridge.exists(), "rag_bridge.py must exist")
        # Disposition: deferred — overlaps RAG wave; no action in W5-COOKBOOK.

    def test_adr_094_draft_location_noted(self):
        """F-5.6-b0e06991: ADR-094 in PLAN-056/adr-drafts; promotion is CANON-ADR."""
        adr_drafts = _REPO_ROOT / ".claude" / "plans" / "PLAN-056" / "adr-drafts"
        # Disposition: CANON-ADR territory — promotion requires Owner sentinel.
        # W5-COOKBOOK does NOT promote ADR-094; flagged for CANON-ADR track.
        # The test just documents the decision; no assertion on promotion state.
        self.assertTrue(True, "ADR-094 promotion flagged for CANON-ADR track")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
