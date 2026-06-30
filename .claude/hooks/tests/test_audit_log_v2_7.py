"""PLAN-020 Phase 0 item 1 — audit_log.py v2.7 cache-header capture tests.

Verifies:
- `_extract_usage_metadata` handles Anthropic shape, missing fields,
  malformed inputs, and legacy non-Anthropic emitters.
- `_compute_cache_coverage` produces correct float OR None (internal
  derivation helper; the emitted field is integer basis-points).
- `_detect_rail` correctly distinguishes native vs custom vs unknown.
- `build_event()` emits the 3 new v2.7 fields (`usage_metadata`,
  `cache_coverage_bps` [PLAN-118 WS-E: int bps, was the float
  `cache_coverage`], `rail`) additively without breaking existing keys.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import audit_log  # noqa: E402


class ExtractUsageMetadataTest(unittest.TestCase):

    def test_full_anthropic_shape(self):
        resp = {
            "usage_metadata": {
                "cache_creation_input_tokens": 1000,
                "cache_read_input_tokens": 500,
                "uncached_input_tokens": 200,
                "output_tokens": 300,
                "thinking_tokens": 50,
            }
        }
        result = audit_log._extract_usage_metadata(resp)
        self.assertEqual(result["cache_creation_input_tokens"], 1000)
        self.assertEqual(result["cache_read_input_tokens"], 500)
        self.assertEqual(result["uncached_input_tokens"], 200)
        self.assertEqual(result["output_tokens"], 300)
        self.assertEqual(result["thinking_tokens"], 50)

    def test_alternate_usage_key(self):
        # Some emitters use `usage` instead of `usage_metadata`
        resp = {
            "usage": {
                "cache_read_input_tokens": 999,
                "output_tokens": 100,
            }
        }
        result = audit_log._extract_usage_metadata(resp)
        self.assertIsNotNone(result)
        self.assertEqual(result["cache_read_input_tokens"], 999)
        self.assertEqual(result["output_tokens"], 100)
        self.assertIsNone(result["cache_creation_input_tokens"])

    def test_missing_usage_metadata_returns_none(self):
        resp = {"text": "hello"}
        self.assertIsNone(audit_log._extract_usage_metadata(resp))

    def test_non_dict_response_returns_none(self):
        for bad in (None, "string", 42, [1, 2], True):
            self.assertIsNone(audit_log._extract_usage_metadata(bad))

    def test_string_int_coercion(self):
        # Some adapters serialize ints as strings
        resp = {
            "usage_metadata": {
                "cache_read_input_tokens": "500",
                "output_tokens": "100",
            }
        }
        result = audit_log._extract_usage_metadata(resp)
        self.assertEqual(result["cache_read_input_tokens"], 500)
        self.assertEqual(result["output_tokens"], 100)

    def test_bool_not_coerced_to_int(self):
        # Defensive: True is technically an int in Python but we reject it
        resp = {"usage_metadata": {"cache_read_input_tokens": True}}
        result = audit_log._extract_usage_metadata(resp)
        self.assertIsNone(result["cache_read_input_tokens"])

    def test_partial_fields(self):
        resp = {"usage_metadata": {"output_tokens": 100}}
        result = audit_log._extract_usage_metadata(resp)
        self.assertEqual(result["output_tokens"], 100)
        self.assertIsNone(result["cache_read_input_tokens"])
        self.assertIsNone(result["thinking_tokens"])

    def test_garbage_field_values(self):
        resp = {
            "usage_metadata": {
                "cache_read_input_tokens": "not-a-number",
                "output_tokens": ["list"],
                "thinking_tokens": {"obj": True},
            }
        }
        result = audit_log._extract_usage_metadata(resp)
        self.assertIsNone(result["cache_read_input_tokens"])
        self.assertIsNone(result["output_tokens"])
        self.assertIsNone(result["thinking_tokens"])


class ComputeCacheCoverageTest(unittest.TestCase):

    def test_full_coverage(self):
        meta = {
            "cache_read_input_tokens": 1000,
            "cache_creation_input_tokens": 0,
            "uncached_input_tokens": 0,
        }
        self.assertEqual(audit_log._compute_cache_coverage(meta), 1.0)

    def test_zero_coverage(self):
        meta = {
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 1000,
            "uncached_input_tokens": 0,
        }
        self.assertEqual(audit_log._compute_cache_coverage(meta), 0.0)

    def test_partial_coverage_50pct(self):
        meta = {
            "cache_read_input_tokens": 500,
            "cache_creation_input_tokens": 250,
            "uncached_input_tokens": 250,
        }
        self.assertEqual(audit_log._compute_cache_coverage(meta), 0.5)

    def test_none_meta_returns_none(self):
        self.assertIsNone(audit_log._compute_cache_coverage(None))

    def test_zero_denominator_returns_none(self):
        meta = {
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "uncached_input_tokens": 0,
        }
        self.assertIsNone(audit_log._compute_cache_coverage(meta))

    def test_missing_fields_treated_as_zero(self):
        meta = {"cache_read_input_tokens": 100}  # only one field
        # denom = 100 + 0 + 0 = 100; coverage = 100/100 = 1.0
        self.assertEqual(audit_log._compute_cache_coverage(meta), 1.0)

    def test_rounded_to_4_decimals(self):
        meta = {
            "cache_read_input_tokens": 1,
            "cache_creation_input_tokens": 2,
            "uncached_input_tokens": 0,
        }
        # 1/3 = 0.3333...
        self.assertEqual(audit_log._compute_cache_coverage(meta), 0.3333)


class DetectRailTest(unittest.TestCase):

    def test_canonical_5_with_reference_is_native(self):
        prompt = "## AGENT PROFILE\n\n## SKILL REFERENCE\n@.claude/skills/core/x/SKILL.md sha256=" + "a" * 64
        for archetype in (
            "code-reviewer",
            "security-engineer",
            "qa-architect",
            "performance-engineer",
            "devops",
        ):
            self.assertEqual(
                audit_log._detect_rail(prompt, archetype),
                "native",
                msg=f"archetype {archetype} should be native",
            )

    def test_legacy_inline_skill_content_is_custom(self):
        prompt = "## AGENT PROFILE\n\n## SKILL CONTENT\n" + "x" * 300
        self.assertEqual(audit_log._detect_rail(prompt, ""), "custom")

    def test_reference_without_canonical_archetype_is_native(self):
        prompt = "## SKILL REFERENCE\n@.claude/skills/x/SKILL.md sha256=" + "a" * 64
        self.assertEqual(
            audit_log._detect_rail(prompt, "frontend-perf-engineer"),
            "native",
        )

    def test_no_skill_marker_returns_none(self):
        self.assertIsNone(audit_log._detect_rail("hello world", "code-reviewer"))

    def test_non_string_prompt_returns_none(self):
        for bad in (None, 42, [], {}):
            self.assertIsNone(audit_log._detect_rail(bad, "code-reviewer"))

    def test_canonical_archetype_without_reference_falls_through(self):
        # If canonical-5 archetype but only has CONTENT (legacy), it's custom
        prompt = "## SKILL CONTENT\n" + "x" * 300
        self.assertEqual(
            audit_log._detect_rail(prompt, "code-reviewer"), "custom"
        )

    def test_both_markers_canonical_prefers_native(self):
        # If somehow both present + canonical, native wins (forward-compat)
        prompt = "## SKILL CONTENT\n" + "x" * 300 + "\n## SKILL REFERENCE\n@x.md sha256=" + "a" * 64
        self.assertEqual(
            audit_log._detect_rail(prompt, "code-reviewer"), "native"
        )


class BuildEntryV27Test(unittest.TestCase):
    """Integration: build_entry() emits the 3 new v2.7 fields additively."""

    def _stub_event(
        self,
        prompt: str = "",
        subagent_type: str = "code-reviewer",
        tool_response=None,
    ):
        if tool_response is None:
            tool_response = {
                "usage_metadata": {
                    "cache_read_input_tokens": 800,
                    "cache_creation_input_tokens": 100,
                    "uncached_input_tokens": 100,
                    "output_tokens": 50,
                    "thinking_tokens": 20,
                },
            }

        class Event:
            pass
        ev = Event()
        ev.tool_name = "Agent"
        ev.session_id = "sess-1"
        ev.subagent_type = subagent_type
        ev.tool_response = tool_response
        ev.description = "stub task description"
        ev.prompt = prompt
        return ev

    def test_entry_has_new_v2_7_keys(self):
        prompt = (
            "## AGENT PROFILE\nName: Code Reviewer\n\n"
            "## SKILL REFERENCE\n"
            "@.claude/skills/core/code-review-checklist/SKILL.md sha256="
            + "a" * 64
        )
        entry = audit_log.build_entry(
            event=self._stub_event(prompt=prompt),
            project_dir="/tmp/test",
            hook_duration_ms=5,
        )
        self.assertIsNotNone(entry)
        self.assertIn("usage_metadata", entry)
        # PLAN-118 WS-E (S181): emitted field is integer basis-points; the
        # legacy float ``cache_coverage`` field must NOT appear (it broke HMAC).
        self.assertIn("cache_coverage_bps", entry)
        self.assertNotIn("cache_coverage", entry)
        self.assertIn("rail", entry)
        self.assertEqual(entry["rail"], "native")
        # 0.8 ratio × 10000 = 8000 bps (int, canonical_json-safe).
        self.assertEqual(entry["cache_coverage_bps"], 8000)
        self.assertIsInstance(entry["cache_coverage_bps"], int)
        self.assertEqual(entry["usage_metadata"]["cache_read_input_tokens"], 800)

    def test_legacy_response_yields_null_cache_fields(self):
        entry = audit_log.build_entry(
            event=self._stub_event(
                prompt="## SKILL CONTENT\n" + "x" * 300,
                subagent_type="",
                tool_response={"text": "hello"},
            ),
            project_dir="/tmp/test",
            hook_duration_ms=5,
        )
        self.assertIsNotNone(entry)
        self.assertIsNone(entry["usage_metadata"])
        self.assertIsNone(entry["cache_coverage_bps"])  # PLAN-118 WS-E
        self.assertNotIn("cache_coverage", entry)
        self.assertEqual(entry["rail"], "custom")  # detected from prompt

    def test_existing_keys_unchanged(self):
        entry = audit_log.build_entry(
            event=self._stub_event(prompt="## SKILL CONTENT\n" + "x" * 300),
            project_dir="/tmp/test",
            hook_duration_ms=10,
        )
        self.assertIsNotNone(entry)
        for required in (
            "ts", "action", "session_id", "project", "tool",
            "subagent_type", "desc_preview", "desc_hash", "skill",
            "has_profile", "has_file_assignment", "prompt_len_bucket",
            "response_kind", "hook_duration_ms",
            "tokens_in", "tokens_out", "tokens_total",
        ):
            self.assertIn(required, entry, msg=f"missing existing key: {required}")


class BuildEntryCanonicalEncodeGuardTest(unittest.TestCase):
    """PLAN-118 WS-E (S181) — class-closure guard for the agent_spawn observer.

    The S164 float-in-HMAC class fix introspected only the ``_lib/audit_emit.py``
    ``emit_*`` functions; it never covered the ``audit_log.py`` observer that
    builds the ``agent_spawn`` entry inline. As a result a float-derived field
    (``cache_coverage``) leaked into the HMAC-covered payload, making
    ``canonical_json.encode()`` raise ``CanonicalJsonError`` → fail-open
    ``hmac:null`` → audit-chain one-way-rule break (whole chain reads ``tamper``).

    These guards assert the OBSERVER-built entry canonical-encodes cleanly for
    the realistic cache-coverage range — ``canonical_json.encode`` IS the
    oracle (it is the exact function ``audit_hmac.compute_entry_hmac`` calls).
    Any future float leaked into ``build_entry`` re-reds these tests.
    """

    def _build(self, cache_read, cache_creation, uncached):
        class Event:
            pass
        ev = Event()
        ev.tool_name = "Agent"
        ev.session_id = "sess-guard"
        ev.subagent_type = "code-reviewer"
        ev.description = "guard task"
        ev.prompt = "## AGENT PROFILE\nName: X\n## SKILL CONTENT\n" + "y" * 300
        ev.tool_response = {
            "usage_metadata": {
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_creation,
                "uncached_input_tokens": uncached,
                "output_tokens": 2222,
            }
        }
        return audit_log.build_entry(
            event=ev, project_dir="/tmp/test", hook_duration_ms=5
        )

    def _encode(self, entry):
        from _lib import canonical_json
        # Raises CanonicalJsonError on any float — the exact failure this
        # guard exists to prevent. No assert needed beyond "does not raise".
        canonical_json.encode(entry)

    def test_prod_value_0_9968_encodes_clean(self):
        # The exact ratio that broke the live chain at S180 (L197):
        # 61773 / (61773 + 201 + ~0) ≈ 0.9968 → 9968 bps.
        entry = self._build(61773, 201, 0)
        self.assertEqual(entry["cache_coverage_bps"], 9968)
        self.assertIsInstance(entry["cache_coverage_bps"], int)
        self.assertNotIn("cache_coverage", entry)
        self._encode(entry)  # must NOT raise CanonicalJsonError

    def test_full_zero_and_mid_coverage_encode_clean(self):
        for cr, cc, un, expect in (
            (1000, 0, 0, 10000),    # 100% coverage
            (0, 500, 500, 0),       # 0% coverage
            (500, 250, 250, 5000),  # 50%
        ):
            entry = self._build(cr, cc, un)
            self.assertEqual(entry["cache_coverage_bps"], expect)
            self.assertIsInstance(entry["cache_coverage_bps"], int)
            self._encode(entry)

    def test_null_coverage_encodes_clean(self):
        # No usage_metadata → cache_coverage_bps is None (still canonical-safe).
        class Event:
            pass
        ev = Event()
        ev.tool_name = "Agent"
        ev.session_id = "sess-guard"
        ev.subagent_type = ""
        ev.description = "no-meta"
        ev.prompt = "## SKILL CONTENT\n" + "z" * 300
        ev.tool_response = {"text": "legacy adapter"}
        entry = audit_log.build_entry(
            event=ev, project_dir="/tmp/test", hook_duration_ms=5
        )
        self.assertIsNone(entry["cache_coverage_bps"])
        self._encode(entry)


if __name__ == "__main__":
    unittest.main()
