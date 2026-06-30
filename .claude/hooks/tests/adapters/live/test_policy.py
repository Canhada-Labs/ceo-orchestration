"""Behavior tests for ``_lib/adapters/live/_policy.py``.

Validates ADR-040 §1-§5 numeric defaults + SPEC §2 validation rules.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[3]

from _lib.adapters.live._policy import (  # noqa: E402
    ClaudeLivePolicy,
    GeminiLivePolicy,
    LiveCallPolicy,
    LocalLivePolicy,
    OpenAILivePolicy,
    default_policy,
)


class TestDefaultsMatchADR040(unittest.TestCase):
    def test_default_numeric_fields_match_adr_040(self):
        p = LiveCallPolicy()
        self.assertEqual(p.connect_timeout_ms, 2500)
        self.assertEqual(p.read_timeout_ms, 8000)
        self.assertEqual(p.max_retries, 1)
        self.assertEqual(p.backoff_initial_ms, 250)
        self.assertEqual(p.backoff_max_ms, 1000)
        self.assertEqual(p.backoff_jitter_pct, 100)
        self.assertEqual(p.breaker_threshold, 5)
        self.assertEqual(p.breaker_window_s, 30)
        self.assertEqual(p.breaker_half_open_s, 60)
        self.assertEqual(p.max_spend_usd_per_spawn, 0.50)
        self.assertEqual(p.max_spend_usd_per_plan_5min, 2.00)
        self.assertEqual(p.max_debate_rounds, 5)
        self.assertEqual(p.credential_max_age_days, 90)
        self.assertEqual(p.credential_warn_age_days, 75)


class TestFactory(unittest.TestCase):
    def test_default_policy_returns_per_provider_subclass(self):
        self.assertIsInstance(default_policy("claude"), ClaudeLivePolicy)
        self.assertIsInstance(default_policy("anthropic"), ClaudeLivePolicy)
        self.assertIsInstance(default_policy("gemini"), GeminiLivePolicy)
        self.assertIsInstance(default_policy("google"), GeminiLivePolicy)
        self.assertIsInstance(default_policy("openai"), OpenAILivePolicy)
        self.assertIsInstance(default_policy("local"), LocalLivePolicy)

    def test_default_policy_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            default_policy("not-a-provider")

    def test_provider_field_set_on_each_subclass(self):
        self.assertEqual(default_policy("claude").provider, "claude")
        self.assertEqual(default_policy("openai").provider, "openai")
        self.assertEqual(default_policy("gemini").provider, "gemini")
        self.assertEqual(default_policy("local").provider, "local")

    def test_credential_env_var_defaults_per_provider(self):
        self.assertEqual(default_policy("claude").credential_env_var, "ANTHROPIC_API_KEY")
        self.assertEqual(default_policy("gemini").credential_env_var, "GOOGLE_API_KEY")
        self.assertEqual(default_policy("openai").credential_env_var, "OPENAI_API_KEY")

    def test_activation_env_var_defaults_per_provider(self):
        self.assertEqual(default_policy("claude").activation_env_var, "CEO_LIVE_CLAUDE")
        self.assertEqual(default_policy("gemini").activation_env_var, "CEO_LIVE_GEMINI")
        self.assertEqual(default_policy("openai").activation_env_var, "CEO_LIVE_OPENAI")
        self.assertEqual(default_policy("local").activation_env_var, "CEO_LIVE_LOCAL")


class TestValidationRules(unittest.TestCase):
    """Each test exercises one rule from SPEC/v1/live-adapters-policy.schema.md §2."""

    def test_rule1_negative_connect_timeout_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(connect_timeout_ms=-1)

    def test_rule1_read_must_exceed_connect(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(connect_timeout_ms=2500, read_timeout_ms=2000)

    def test_rule2_max_retries_capped_at_3(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(max_retries=4)

    def test_rule3_backoff_max_lt_initial_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(backoff_initial_ms=500, backoff_max_ms=200)

    def test_rule3_backoff_max_above_5000_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(backoff_max_ms=6000)

    def test_rule4_breaker_threshold_min_2(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(breaker_threshold=1)

    def test_rule5_spawn_ceiling_must_be_positive(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(max_spend_usd_per_spawn=0.0)

    def test_rule5_spawn_ceiling_capped_by_plan(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(max_spend_usd_per_spawn=5.0, max_spend_usd_per_plan_5min=2.0)

    def test_rule6_warn_must_be_strictly_below_max_age(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(credential_warn_age_days=90, credential_max_age_days=90)

    def test_rule7_unknown_scope_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(scope="full_access")

    def test_rule8_openai_embeddings_require_opt_out(self):
        with self.assertRaises(ValueError):
            OpenAILivePolicy(scope="embeddings_only", data_retention_opt_out=False)

    def test_rule8_openai_embeddings_require_header(self):
        with self.assertRaises(ValueError):
            OpenAILivePolicy(
                scope="embeddings_only",
                data_retention_opt_out=True,
                data_retention_opt_out_header=None,
            )

    def test_rule9_empty_leak_patterns_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(leak_detection_patterns=[])

    def test_rule10_activation_env_must_match_pattern(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(activation_env_var="NOT_PREFIXED")

    def test_unknown_provider_rejected(self):
        with self.assertRaises(ValueError):
            ClaudeLivePolicy(provider="not-a-provider")


class TestImmutability(unittest.TestCase):
    def test_policy_is_frozen(self):
        p = ClaudeLivePolicy()
        with self.assertRaises(Exception):
            p.connect_timeout_ms = 9999  # type: ignore[misc]

    def test_replace_creates_new_validated_instance(self):
        p = ClaudeLivePolicy()
        p2 = replace(p, breaker_threshold=10)
        self.assertEqual(p2.breaker_threshold, 10)
        self.assertEqual(p.breaker_threshold, 5)


class TestOpenAIScopeConfiguration(unittest.TestCase):
    def test_default_openai_chat_only_works_without_opt_out(self):
        # chat_only doesn't trigger opt-out invariant
        p = OpenAILivePolicy(scope="chat_only", data_retention_opt_out=False)
        self.assertEqual(p.scope, "chat_only")

    def test_openai_chat_and_embeddings_requires_opt_out(self):
        with self.assertRaises(ValueError):
            OpenAILivePolicy(scope="chat_and_embeddings", data_retention_opt_out=False)


if __name__ == "__main__":
    unittest.main()
