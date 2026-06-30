"""Tests for `_lib/adapters/live/claude.py` thinking auto-inject (E6-F2).

PLAN-091 Wave A.3 — `/effort` slash command auto-injects extended-thinking
config into the Anthropic Messages API call when caller does not pass an
explicit ``thinking=`` kwarg. PLAN-134 W0 E6-F2 — the resolver is
model-aware: adaptive-only ids (Opus 4.6+/Sonnet 4.6/Opus 4.7/4.8/Fable 5)
get ``thinking={"type": "adaptive"}`` + ``output_config.effort``; legacy
(pre-4.6) ids keep ``{"type": "enabled", "budget_tokens": N}``.

Invariants pinned here (E6-F2 regression contract):

1. The request body NEVER contains ``budget_tokens`` for adaptive-only
   model ids (claude-opus-4-7 / claude-opus-4-8 / claude-fable-5 — the
   legacy shape is HTTP 400 there; also 4.6 family by chosen policy).
2. ``CEO_EFFORT_OVERRIDE`` resolves to adaptive thinking +
   ``output_config.effort`` on adaptive-only ids.
3. ``off`` / ``CEO_THINKING_AUTO_DISABLE=1`` → NO ``thinking`` key at all
   (never ``{"type": "disabled"}`` — HTTP 400 on Fable 5).
4. The ``interleaved-thinking-2025-05-14`` beta header is legacy-only —
   never added when thinking.type == "adaptive".
5. An explicit caller-passed legacy dict on an adaptive-only model is
   translated to ``{"type": "adaptive"}`` (hard guard).

Stdlib only. ``TestEnvContext`` from ``_lib/testing.py`` for env isolation.
"""
from __future__ import annotations

import json as _json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.adapters.live import claude as claude_live  # noqa: E402

# Adaptive-only ids that 400 on the legacy enabled/budget shape.
_ADAPTIVE_IDS = ("claude-opus-4-7", "claude-opus-4-8", "claude-fable-5")
# A pre-4.6 id that still takes the legacy enabled/budget shape.
_LEGACY_MODEL = "claude-sonnet-4-5"


class TestIsAdaptiveOnly(TestEnvContext):
    """`_is_adaptive_only()` allowlist-prefix predicate."""

    def test_current_generation_ids_match(self):
        for model in (
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
            "claude-opus-4-8",
            "claude-fable-5",
        ):
            self.assertTrue(claude_live._is_adaptive_only(model), model)

    def test_prefix_match_covers_date_suffixed_ids(self):
        self.assertTrue(
            claude_live._is_adaptive_only("claude-opus-4-8-20260301")
        )

    def test_legacy_ids_do_not_match(self):
        for model in ("claude-sonnet-4-5", "claude-opus-4-1", "claude-haiku-4-5"):
            self.assertFalse(claude_live._is_adaptive_only(model), model)

    def test_non_str_is_false(self):
        self.assertFalse(claude_live._is_adaptive_only(None))


class TestResolveEffortConfig(TestEnvContext):
    """`_resolve_effort_config()` env-var → (thinking, output_config)."""

    def _resolve(self, model):
        return claude_live._resolve_effort_config(model)

    # --- shared fail-soft behavior -------------------------------------

    def test_returns_none_pair_when_env_absent(self):
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        self.assertEqual(self._resolve("claude-opus-4-8"), (None, None))
        self.assertEqual(self._resolve(_LEGACY_MODEL), (None, None))

    def test_returns_none_pair_when_env_empty(self):
        os.environ["CEO_EFFORT_OVERRIDE"] = ""
        self.assertEqual(self._resolve("claude-opus-4-8"), (None, None))

    def test_returns_none_pair_when_off(self):
        # Invariant 3: `off` OMITS thinking entirely — never type=disabled.
        os.environ["CEO_EFFORT_OVERRIDE"] = "off"
        self.assertEqual(self._resolve("claude-opus-4-8"), (None, None))
        self.assertEqual(self._resolve(_LEGACY_MODEL), (None, None))

    def test_returns_none_pair_for_unknown_token(self):
        os.environ["CEO_EFFORT_OVERRIDE"] = "definitely-not-a-valid-effort"
        self.assertEqual(self._resolve("claude-opus-4-8"), (None, None))
        self.assertEqual(self._resolve(_LEGACY_MODEL), (None, None))

    # --- adaptive-only surface (invariants 1 + 2) ----------------------

    def test_adaptive_levels_map_to_effort_strings(self):
        expected = {"low": "low", "med": "medium", "high": "high", "max": "max"}
        for keyword, level in expected.items():
            os.environ["CEO_EFFORT_OVERRIDE"] = keyword
            thinking, output_config = self._resolve("claude-opus-4-8")
            self.assertEqual(thinking, {"type": "adaptive"}, keyword)
            self.assertEqual(output_config, {"effort": level}, keyword)

    def test_adaptive_resolution_for_every_adaptive_id(self):
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        for model in _ADAPTIVE_IDS + ("claude-opus-4-6", "claude-sonnet-4-6"):
            thinking, output_config = self._resolve(model)
            self.assertEqual(thinking, {"type": "adaptive"}, model)
            self.assertEqual(output_config, {"effort": "high"}, model)
            self.assertNotIn("budget_tokens", thinking, model)

    # --- legacy surface (kept for pre-4.6 ids) -------------------------

    def test_legacy_levels_map_to_budgets(self):
        expected = {"low": 1024, "med": 4096, "high": 16384, "max": 32768}
        for keyword, budget in expected.items():
            os.environ["CEO_EFFORT_OVERRIDE"] = keyword
            thinking, output_config = self._resolve(_LEGACY_MODEL)
            self.assertEqual(
                thinking, {"type": "enabled", "budget_tokens": budget}, keyword
            )
            self.assertIsNone(output_config, keyword)

    # --- normalization --------------------------------------------------

    def test_case_insensitive(self):
        os.environ["CEO_EFFORT_OVERRIDE"] = "HIGH"
        thinking, output_config = self._resolve("claude-opus-4-8")
        self.assertEqual(thinking, {"type": "adaptive"})
        self.assertEqual(output_config, {"effort": "high"})

    def test_whitespace_stripped(self):
        os.environ["CEO_EFFORT_OVERRIDE"] = "  med  "
        thinking, output_config = self._resolve("claude-fable-5")
        self.assertEqual(output_config, {"effort": "medium"})


class _FakeTransport:
    """Minimal transport stub — captures body for assertion + replays response."""

    def __init__(self):
        self.captured_body = None
        self.captured_headers = None
        self.captured_url = None

    def post_json(self, url, headers, body):
        self.captured_url = url
        self.captured_headers = headers
        self.captured_body = body
        # Return None for failure-mode triggering simplest fallback. The
        # body capture happens before transport runs, so test assertions
        # work regardless of outcome.

        class _FailureStub:
            failure_mode = "transport_stub"
            http_status = None
            duration_ms = 1
            retried = False
        return None, _FailureStub()


class TestAdapterCallIntegration(TestEnvContext):
    """`ClaudeLiveAdapter.call()` thinking-injection behavior."""

    def _make_adapter(self, transport):
        from _lib.adapters.live._policy import ClaudeLivePolicy
        return claude_live.ClaudeLiveAdapter(
            policy=ClaudeLivePolicy(), transport=transport
        )

    def _enable_live(self):
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-stub"
        # PLAN-085 Wave C.1 — live adapter consults .claude/settings.json
        # for live_adapter_allowlist; fail-CLOSED on missing file. Write a
        # minimal fixture that grants `claude` so activation gate passes.
        settings = self.project_dir / ".claude" / "settings.json"
        settings.write_text(
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_caller_thinking_preserved_on_legacy_model(self):
        self._enable_live()
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        explicit = {"type": "enabled", "budget_tokens": 8000}
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking=explicit,
        )
        self.assertIsNotNone(t.captured_body)
        self.assertEqual(t.captured_body.get("thinking"), explicit)

    def test_caller_legacy_dict_translated_on_adaptive_only(self):
        """Invariant 5: explicit legacy dict on adaptive-only id → adaptive."""
        self._enable_live()
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        for model in _ADAPTIVE_IDS:
            t = _FakeTransport()
            adapter = self._make_adapter(t)
            adapter.call(
                messages=[{"role": "user", "content": "hi"}],
                model=model,
                thinking={"type": "enabled", "budget_tokens": 8000},
            )
            self.assertEqual(
                t.captured_body.get("thinking"), {"type": "adaptive"}, model
            )
            self.assertNotIn("budget_tokens", _json.dumps(t.captured_body), model)

    def test_caller_disabled_dict_removed_on_adaptive_only(self):
        """Explicit {"type": "disabled"} on Fable 5 → NO thinking key.

        An explicit disabled dict is an HTTP 400 on claude-fable-5; the
        normalization guard must REMOVE the key entirely (omission is the
        only safe spelling).
        """
        self._enable_live()
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-fable-5",
            thinking={"type": "disabled"},
        )
        self.assertIsNotNone(t.captured_body)
        self.assertNotIn("thinking", t.captured_body)
        self.assertNotIn("disabled", _json.dumps(t.captured_body))

    def test_caller_adaptive_with_budget_tokens_stripped_on_adaptive_only(self):
        """{"type": "adaptive", "budget_tokens": N} on Fable 5 → budget stripped."""
        self._enable_live()
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-fable-5",
            thinking={"type": "adaptive", "budget_tokens": 1024},
        )
        self.assertEqual(
            t.captured_body.get("thinking"), {"type": "adaptive"}
        )
        self.assertNotIn("budget_tokens", _json.dumps(t.captured_body))

    def test_effort_override_injects_adaptive_on_current_generation(self):
        """Invariant 2: adaptive + output_config.effort from /effort."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-opus-4-8",
            thinking=None,
        )
        self.assertEqual(t.captured_body.get("thinking"), {"type": "adaptive"})
        self.assertEqual(t.captured_body.get("output_config"), {"effort": "high"})

    def test_effort_override_never_emits_budget_tokens_on_adaptive_ids(self):
        """Invariant 1: no budget_tokens anywhere in the body for 4.7+/Fable."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "max"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        for model in _ADAPTIVE_IDS:
            t = _FakeTransport()
            adapter = self._make_adapter(t)
            adapter.call(
                messages=[{"role": "user", "content": "hi"}],
                model=model,
            )
            self.assertNotIn("budget_tokens", _json.dumps(t.captured_body), model)
            self.assertEqual(
                t.captured_body.get("thinking"), {"type": "adaptive"}, model
            )

    def test_effort_override_keeps_legacy_shape_on_pre_46_model(self):
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking=None,
        )
        self.assertEqual(
            t.captured_body.get("thinking"),
            {"type": "enabled", "budget_tokens": 16384},
        )
        self.assertNotIn("output_config", t.captured_body)

    def test_caller_wins_over_effort_override(self):
        """Explicit caller dict beats CEO_EFFORT_OVERRIDE auto-inject."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "max"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        explicit = {"type": "enabled", "budget_tokens": 2000}
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking=explicit,
        )
        # The explicit caller value (2000) MUST win over /effort=max (32768).
        self.assertEqual(t.captured_body.get("thinking"), explicit)
        self.assertNotIn("output_config", t.captured_body)

    def test_kill_switch_drops_effort_inject(self):
        """Invariant 3: kill-switch → no thinking AND no output_config."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        os.environ["CEO_THINKING_AUTO_DISABLE"] = "1"
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-opus-4-8",
        )
        self.assertNotIn("thinking", t.captured_body)
        self.assertNotIn("output_config", t.captured_body)

    def test_kill_switch_drops_caller_thinking_too(self):
        """Kill switch wins over caller-passed thinking as well."""
        self._enable_live()
        os.environ["CEO_THINKING_AUTO_DISABLE"] = "1"
        explicit = {"type": "enabled", "budget_tokens": 8000}
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking=explicit,
        )
        self.assertNotIn("thinking", t.captured_body)

    def test_no_env_no_caller_no_thinking_field(self):
        """When neither caller nor /effort sets thinking, field is absent."""
        self._enable_live()
        os.environ.pop("CEO_EFFORT_OVERRIDE", None)
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-opus-4-8",
        )
        self.assertNotIn("thinking", t.captured_body)
        self.assertNotIn("output_config", t.captured_body)

    def test_effort_off_omits_thinking_entirely(self):
        """Invariant 3: off → NO thinking key (never {"type": "disabled"})."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "off"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        for model in _ADAPTIVE_IDS + (_LEGACY_MODEL,):
            t = _FakeTransport()
            adapter = self._make_adapter(t)
            adapter.call(
                messages=[{"role": "user", "content": "hi"}],
                model=model,
            )
            self.assertNotIn("thinking", t.captured_body, model)
            self.assertNotIn("output_config", t.captured_body, model)
            self.assertNotIn("disabled", _json.dumps(t.captured_body), model)


class _ResponseStubTransport:
    """Transport stub that replays a fixed 2xx response (for response-parse tests)."""

    def __init__(self, body_obj, status=200):
        self._body = _json.dumps(body_obj).encode("utf-8")
        self._status = status
        self.captured_body = None

    def post_json(self, url, headers, body):
        self.captured_body = body

        class _Resp:
            pass

        r = _Resp()
        r.status = self._status
        r.body_bytes = self._body
        r.duration_ms = 1
        r.retried = False
        return r, None


class TestCookbookRequestConstruction(TestEnvContext):
    """PLAN-113 W5 — COOK-P1 strict-JSON + COOK-P3 documents + cache_control.

    All wirings are additive caller-opt-in kwargs: the request body is
    byte-identical to the pre-W5 baseline when the kwargs are absent.
    """

    def _make_adapter(self, transport):
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
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    # --- COOK-P1 strict-JSON request side -----------------------------

    def test_tools_and_tool_choice_passed_through(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        tools = [{"name": "emit_verdict", "input_schema": {"type": "object"}}]
        tool_choice = {"type": "tool", "name": "emit_verdict"}
        adapter.call(
            messages=[{"role": "user", "content": "review"}],
            model="claude-opus-4-8",
            tools=tools,
            tool_choice=tool_choice,
        )
        self.assertEqual(t.captured_body.get("tools"), tools)
        self.assertEqual(t.captured_body.get("tool_choice"), tool_choice)

    def test_response_format_passed_through(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        rf = {"type": "json_schema", "json_schema": {"name": "x"}}
        adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
            response_format=rf,
        )
        self.assertEqual(t.captured_body.get("response_format"), rf)

    def test_no_cook_kwargs_means_no_extra_fields(self):
        """Baseline: absent kwargs → no tools/tool_choice/response_format/system."""
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
        )
        for k in ("tools", "tool_choice", "response_format", "system"):
            self.assertNotIn(k, t.captured_body)

    # --- COOK-P3 Citations request side -------------------------------

    def test_citation_document_blocks_passed_through_in_messages(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "document",
                 "source": {"type": "text", "media_type": "text/plain",
                            "data": "DOC"},
                 "citations": {"enabled": True}},
                {"type": "text", "text": "cite the source"},
            ],
        }]
        adapter.call(messages=msgs, model="claude-opus-4-8")
        self.assertEqual(t.captured_body["messages"], msgs)
        self.assertEqual(
            t.captured_body["messages"][0]["content"][0]["citations"],
            {"enabled": True},
        )

    # --- cache_control:ephemeral marker -------------------------------

    def test_cache_control_stamps_system_string(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
            system="big stable system prompt",
            cache_control=True,
        )
        sys_block = t.captured_body["system"]
        self.assertEqual(
            sys_block,
            [{"type": "text", "text": "big stable system prompt",
              "cache_control": {"type": "ephemeral"}}],
        )

    def test_cache_control_off_does_not_mark(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
            system="sys",
        )
        # system passes through verbatim; no ephemeral marker injected.
        self.assertEqual(t.captured_body["system"], "sys")

    def test_cache_control_stamps_first_message_when_no_system(self):
        self._enable_live()
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "stable prefix"}],
            model="claude-opus-4-8",
            cache_control=True,
        )
        content = t.captured_body["messages"][0]["content"]
        self.assertEqual(
            content,
            [{"type": "text", "text": "stable prefix",
              "cache_control": {"type": "ephemeral"}}],
        )

    # --- COOK-P1 strict-JSON response recovery ------------------------

    def test_tool_use_input_surfaced_as_text_when_no_prose(self):
        self._enable_live()
        body = {
            "content": [
                {"type": "tool_use", "name": "emit_verdict",
                 "input": {"verdict": "ACCEPT", "must_fix": []}},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        t = _ResponseStubTransport(body)
        adapter = self._make_adapter(t)
        result = adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
            tools=[{"name": "emit_verdict"}],
            tool_choice={"type": "tool", "name": "emit_verdict"},
        )
        self.assertTrue(result.success)
        self.assertEqual(
            _json.loads(result.text),
            {"verdict": "ACCEPT", "must_fix": []},
        )

    def test_prose_text_preferred_over_tool_use(self):
        self._enable_live()
        body = {
            "content": [
                {"type": "text", "text": "hello prose"},
                {"type": "tool_use", "name": "t", "input": {"a": 1}},
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        t = _ResponseStubTransport(body)
        adapter = self._make_adapter(t)
        result = adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-8",
        )
        self.assertEqual(result.text, "hello prose")


class TestInterleavedThinkingGuard(TestEnvContext):
    """P1 fix + E6-F2 invariant 4: interleaved beta header is LEGACY-only.

    interleaved_thinking=True with NO active legacy thinking block (or
    thinking dropped by kill-switch, or adaptive thinking) is an invalid
    Anthropic request — the beta header and body field must be dropped.
    Adaptive thinking auto-interleaves; the header must never appear.
    """

    def _make_adapter(self, transport):
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
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_interleaved_thinking_without_thinking_block_is_noop(self):
        """interleaved_thinking=True + no thinking → no beta header, no body field."""
        self._enable_live()
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking=None,             # no thinking block
            interleaved_thinking=True, # opt-in: should be ignored without thinking
        )
        self.assertIsNotNone(t.captured_body)
        self.assertNotIn("interleaved_thinking", t.captured_body,
                         "interleaved_thinking field must NOT appear without active thinking")
        self.assertNotIn("anthropic-beta", t.captured_headers or {},
                         "beta header must NOT appear without active thinking")

    def test_interleaved_thinking_with_thinking_disabled_body_is_noop(self):
        """interleaved_thinking=True + thinking.type=disabled → no beta header."""
        self._enable_live()
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking={"type": "disabled"},   # thinking block present but NOT enabled
            interleaved_thinking=True,
        )
        self.assertNotIn("interleaved_thinking", t.captured_body)
        self.assertNotIn("anthropic-beta", t.captured_headers or {})

    def test_interleaved_thinking_with_active_legacy_thinking_adds_header(self):
        """interleaved_thinking=True + LEGACY thinking.type=enabled → header + field."""
        self._enable_live()
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking={"type": "enabled", "budget_tokens": 1024},
            interleaved_thinking=True,
        )
        self.assertEqual(t.captured_body.get("interleaved_thinking"), True,
                         "interleaved_thinking field MUST appear when legacy thinking is enabled")
        beta = (t.captured_headers or {}).get("anthropic-beta", "")
        self.assertIn("interleaved-thinking-2025-05-14", beta,
                      "beta header MUST appear when legacy thinking is enabled")

    def test_no_interleaved_header_on_adaptive_thinking(self):
        """Invariant 4: adaptive thinking auto-interleaves — header never added."""
        self._enable_live()
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-opus-4-8",
            interleaved_thinking=True,
        )
        self.assertEqual(t.captured_body.get("thinking"), {"type": "adaptive"})
        self.assertNotIn("interleaved_thinking", t.captured_body)
        self.assertNotIn("anthropic-beta", t.captured_headers or {})

    def test_no_interleaved_header_when_legacy_dict_translated(self):
        """Caller legacy dict on adaptive-only id → translated → no header."""
        self._enable_live()
        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-fable-5",
            thinking={"type": "enabled", "budget_tokens": 1024},
            interleaved_thinking=True,
        )
        self.assertEqual(t.captured_body.get("thinking"), {"type": "adaptive"})
        self.assertNotIn("interleaved_thinking", t.captured_body)
        self.assertNotIn("anthropic-beta", t.captured_headers or {})

    def test_interleaved_thinking_kill_switch_overrides_active_thinking(self):
        """CEO_INTERLEAVED_THINKING_DISABLE=1 suppresses even when thinking is on."""
        self._enable_live()
        os.environ["CEO_INTERLEAVED_THINKING_DISABLE"] = "1"
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking={"type": "enabled", "budget_tokens": 1024},
            interleaved_thinking=True,
        )
        self.assertNotIn("interleaved_thinking", t.captured_body)
        self.assertNotIn("anthropic-beta", t.captured_headers or {})

    def test_interleaved_thinking_none_is_default_off(self):
        """interleaved_thinking=None (default) → no beta header, no body field."""
        self._enable_live()
        os.environ.pop("CEO_INTERLEAVED_THINKING_DISABLE", None)
        t = _FakeTransport()
        adapter = self._make_adapter(t)
        adapter.call(
            messages=[{"role": "user", "content": "hi"}],
            model=_LEGACY_MODEL,
            thinking={"type": "enabled", "budget_tokens": 1024},
            # interleaved_thinking intentionally omitted (default None)
        )
        self.assertNotIn("interleaved_thinking", t.captured_body)
        self.assertNotIn("anthropic-beta", t.captured_headers or {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
