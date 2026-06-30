"""PLAN-086 Wave D — MCP routing resolver tests (AC D.3 + D.4).

48-case matrix: 12 servers × 4 task classes. Plus correctness suites.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import mcp_routing  # noqa: E402

_ALL_SERVERS = mcp_routing.BUNDLE_SERVERS
_FOUR_TASK_CLASSES = ("file_read", "line_audit", "debate", "arch")


class TestBundleCompleteness(unittest.TestCase):
    def test_bundle_has_12_servers(self) -> None:
        self.assertEqual(len(_ALL_SERVERS), 12)

    def test_contains_canonical_set(self) -> None:
        for s in ("Vercel", "Stripe", "Ahrefs", "LunarCrush",
                  "claude-in-chrome", "Supabase", "Gmail",
                  "Google_Calendar", "Google_Drive", "Sentry",
                  "Cloudflare_Developer_Platform", "Similarweb"):
            self.assertIn(s, _ALL_SERVERS)


class TestKillSwitchEnvDeriv(unittest.TestCase):
    def test_stripe(self) -> None:
        self.assertEqual(mcp_routing._kill_switch_env("Stripe"),
                         "CEO_MCP_STRIPE_DISABLE")

    def test_claude_in_chrome(self) -> None:
        self.assertEqual(mcp_routing._kill_switch_env("claude-in-chrome"),
                         "CEO_MCP_CLAUDE_IN_CHROME_DISABLE")

    def test_cloudflare(self) -> None:
        self.assertEqual(
            mcp_routing._kill_switch_env("Cloudflare_Developer_Platform"),
            "CEO_MCP_CLOUDFLARE_DEVELOPER_PLATFORM_DISABLE",
        )

    def test_lunarcrush(self) -> None:
        self.assertEqual(mcp_routing._kill_switch_env("LunarCrush"),
                         "CEO_MCP_LUNARCRUSH_DISABLE")


class TestMatrixBase(unittest.TestCase):
    """One subclass per server. Each tests 4 task classes = 48 cases total."""
    server: str = ""

    def _ks_env(self) -> str:
        return mcp_routing._kill_switch_env(self.server)

    def test_file_read_returns_none(self) -> None:
        with patch.dict(os.environ, {"CEO_SOTA_DISABLE": "0"}, clear=False):
            self.assertIsNone(mcp_routing.resolve("file_read"))

    def test_line_audit_returns_none(self) -> None:
        with patch.dict(os.environ, {"CEO_SOTA_DISABLE": "0"}, clear=False):
            self.assertIsNone(mcp_routing.resolve("line_audit"))

    def test_debate_returns_none(self) -> None:
        with patch.dict(os.environ, {"CEO_SOTA_DISABLE": "0"}, clear=False):
            self.assertIsNone(mcp_routing.resolve("debate"))

    def test_arch_returns_vercel(self) -> None:
        with patch.dict(
            os.environ,
            {"CEO_SOTA_DISABLE": "0", "CEO_MCP_VERCEL_DISABLE": "0"},
            clear=False,
        ):
            self.assertEqual(mcp_routing.resolve("arch"), "Vercel")


# Generate 12 subclasses dynamically (12 × 4 = 48 cases for AC D.3).
for _server in _ALL_SERVERS:
    _safe = _server.replace("-", "_").replace(" ", "_")
    _cls = type(f"TestMatrix_{_safe}", (TestMatrixBase,), {"server": _server})
    globals()[_cls.__name__] = _cls

del _server, _safe, _cls


class TestPositiveRouting(unittest.TestCase):
    def setUp(self) -> None:
        self._p = patch.dict(os.environ, {
            "CEO_SOTA_DISABLE": "0",
            "CEO_MCP_VERCEL_DISABLE": "0",
            "CEO_MCP_STRIPE_DISABLE": "0",
            "CEO_MCP_AHREFS_DISABLE": "0",
            "CEO_MCP_LUNARCRUSH_DISABLE": "0",
        }, clear=False)
        self._p.start()

    def tearDown(self) -> None:
        self._p.stop()

    def test_arch_vercel(self) -> None:
        self.assertEqual(mcp_routing.resolve("arch"), "Vercel")

    def test_finops_stripe(self) -> None:
        self.assertEqual(mcp_routing.resolve("finops"), "Stripe")

    def test_seo_ahrefs(self) -> None:
        self.assertEqual(mcp_routing.resolve("seo_research"), "Ahrefs")

    def test_crypto_lunarcrush(self) -> None:
        self.assertEqual(mcp_routing.resolve("crypto_research"), "LunarCrush")

    def test_route_alias(self) -> None:
        self.assertIs(mcp_routing.route, mcp_routing.resolve)


class TestKillSwitches(unittest.TestCase):
    def test_per_server_kill_switch_suppresses(self) -> None:
        with patch.dict(os.environ, {
            "CEO_MCP_VERCEL_DISABLE": "1",
            "CEO_SOTA_DISABLE": "0",
        }, clear=False):
            self.assertIsNone(mcp_routing.resolve("arch"))

    def test_global_kill_switch_suppresses_all(self) -> None:
        with patch.dict(os.environ, {"CEO_SOTA_DISABLE": "1"}, clear=False):
            for tc in ("arch", "finops", "seo_research", "crypto_research"):
                self.assertIsNone(mcp_routing.resolve(tc))

    def test_value_0_not_kill(self) -> None:
        with patch.dict(os.environ, {
            "CEO_MCP_VERCEL_DISABLE": "0",
            "CEO_SOTA_DISABLE": "0",
        }, clear=False):
            self.assertEqual(mcp_routing.resolve("arch"), "Vercel")

    def test_unknown_task_class_returns_none(self) -> None:
        with patch.dict(os.environ, {"CEO_SOTA_DISABLE": "0"}, clear=False):
            self.assertIsNone(mcp_routing.resolve("totally_unknown"))


class TestEmitShim(unittest.TestCase):
    """AC D.4 — best-effort emit must never break routing."""

    def test_emit_no_op_when_audit_emit_unavailable(self) -> None:
        original = mcp_routing._audit_emit_mod
        original_tried = mcp_routing._audit_emit_tried
        try:
            mcp_routing._audit_emit_mod = None
            mcp_routing._audit_emit_tried = True
            mcp_routing._emit_advisory("arch", "Vercel", "")
        finally:
            mcp_routing._audit_emit_mod = original
            mcp_routing._audit_emit_tried = original_tried

    def test_emit_skipped_when_action_unregistered(self) -> None:
        mock_ae = MagicMock()
        mock_ae._KNOWN_ACTIONS = frozenset({"other_action"})
        original = mcp_routing._audit_emit_mod
        original_tried = mcp_routing._audit_emit_tried
        try:
            mcp_routing._audit_emit_mod = mock_ae
            mcp_routing._audit_emit_tried = True
            mcp_routing._emit_advisory("arch", "Vercel", "")
            mock_ae.emit_generic.assert_not_called()
        finally:
            mcp_routing._audit_emit_mod = original
            mcp_routing._audit_emit_tried = original_tried

    def test_emit_called_when_registered(self) -> None:
        mock_ae = MagicMock()
        mock_ae._KNOWN_ACTIONS = frozenset({"mcp_route_advised"})
        original = mcp_routing._audit_emit_mod
        original_tried = mcp_routing._audit_emit_tried
        try:
            mcp_routing._audit_emit_mod = mock_ae
            mcp_routing._audit_emit_tried = True
            mcp_routing._emit_advisory("arch", "Vercel", "")
            mock_ae.emit_generic.assert_called_once()
        finally:
            mcp_routing._audit_emit_mod = original
            mcp_routing._audit_emit_tried = original_tried

    def test_emit_fields_are_allowlist_subset(self) -> None:
        # Regression: S169 audit-log.errors triage. _emit_advisory previously
        # passed server/kill_switch_active/global_disable, none of which are in
        # _MCP_ROUTE_ADVISED_ALLOWLIST, so they were silently scrubbed on every
        # emit and the recorded events lost their AML.T0050 payload. Cross-check
        # every emitted kwarg against the real allowlist (source of truth) so
        # any future caller/schema drift fails here.
        from _lib import audit_emit  # noqa: E402

        mock_ae = MagicMock()
        mock_ae._KNOWN_ACTIONS = frozenset({"mcp_route_advised"})
        original = mcp_routing._audit_emit_mod
        original_tried = mcp_routing._audit_emit_tried
        try:
            mcp_routing._audit_emit_mod = mock_ae
            mcp_routing._audit_emit_tried = True
            mcp_routing._emit_advisory("arch", "Vercel", "CEO_MCP_VERCEL_DISABLE")
            args, kwargs = mock_ae.emit_generic.call_args
            self.assertEqual(args[0], "mcp_route_advised")
            # Every emitted field must be permitted by the canonical allowlist.
            self.assertTrue(
                set(kwargs).issubset(audit_emit._MCP_ROUTE_ADVISED_ALLOWLIST),
                f"emitted non-allowlisted field(s): "
                f"{set(kwargs) - audit_emit._MCP_ROUTE_ADVISED_ALLOWLIST}",
            )
            self.assertEqual(kwargs["task_class"], "arch")
            self.assertEqual(kwargs["suggested_servers"], "Vercel")
            self.assertEqual(kwargs["kill_switch_overrides"], "CEO_MCP_VERCEL_DISABLE")
            self.assertEqual(kwargs["signal_source"], "mcp_task_class")
            for forbidden in ("server", "kill_switch_active", "global_disable"):
                self.assertNotIn(forbidden, kwargs)
        finally:
            mcp_routing._audit_emit_mod = original
            mcp_routing._audit_emit_tried = original_tried

    def test_emit_exception_does_not_break_resolve(self) -> None:
        mock_ae = MagicMock()
        mock_ae._KNOWN_ACTIONS = frozenset({"mcp_route_advised"})
        mock_ae.emit_generic.side_effect = RuntimeError("audit infra down")
        original = mcp_routing._audit_emit_mod
        original_tried = mcp_routing._audit_emit_tried
        try:
            mcp_routing._audit_emit_mod = mock_ae
            mcp_routing._audit_emit_tried = True
            with patch.dict(os.environ, {
                "CEO_SOTA_DISABLE": "0",
                "CEO_MCP_VERCEL_DISABLE": "0",
            }, clear=False):
                result = mcp_routing.resolve("arch")
            self.assertEqual(result, "Vercel")
        finally:
            mcp_routing._audit_emit_mod = original
            mcp_routing._audit_emit_tried = original_tried


if __name__ == "__main__":
    unittest.main()
