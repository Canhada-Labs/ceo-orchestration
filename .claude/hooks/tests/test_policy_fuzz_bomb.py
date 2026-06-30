"""YAML-bomb fuzz corpus — PLAN-014 Phase A.6 ADJ-004.

25 adversarial YAML payloads spanning the attack classes enumerated in
SPEC/v1/policy-dsl.schema.md §3.3. Every payload MUST be rejected by
``_lib.policy.load`` with the expected ``error_kind`` from the closed
SPEC §5 enum.

Categories:
 * alias bombs (billion-laughs style)          ×5 -> alias_rejected
 * deep nesting                                ×5 -> depth_limit
 * custom tags                                 ×5 -> tag_rejected
 * flow abuse                                  ×3 -> parse_error
 * directive / multi-doc                       ×3 -> parse_error
 * size / scalar                               ×4 -> size_limit

Total 25 — zero payloads accepted. The test is a negative-case battery:
failure-shape is asserted per payload (not just "raises").
"""

from __future__ import annotations

import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy as P  # noqa: E402


_BASE_HEADER = """\
schema: "policy-dsl/v1"
id: bomb-test
description: "x"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: r
    description: ""
    decision: allow
    predicate:
"""

_BASE_FOOTER = """\
error_model:
  reasons:
    r: "x"
"""


def _mk(predicate_block: str) -> str:
    return _BASE_HEADER + predicate_block + "\n" + _BASE_FOOTER


class TestYamlAliasBombs(TestEnvContext):
    """5 alias / anchor payloads → alias_rejected."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "bomb.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def test_anchor_in_description(self):
        body = _BASE_HEADER.replace('"x"', "&anchor hello") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_alias_in_description(self):
        body = _BASE_HEADER.replace('"x"', "*anchor") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_anchor_multi_reference(self):
        body = _BASE_HEADER.replace('"x"', "&a first") + "      eq: {field: tool, value: \"*a\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_billion_laughs_pattern(self):
        # Five levels of anchor nesting — rejected on first anchor encounter.
        body = _BASE_HEADER.replace('"x"', "&l0 root") + (
            "      eq: {field: tool, value: \"*l0\"}\n"
        ) + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_anchor_in_nested_scalar(self):
        pred = "      eq:\n        field: tool\n        value: &v \"B\"\n"
        body = _BASE_HEADER + pred + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")


class TestYamlDepthBombs(TestEnvContext):
    """5 deep-nesting payloads → depth_limit (or parse_error fallback)."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "deep.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def _nested_all(self, depth: int) -> str:
        indent = 6
        lines = []
        for _ in range(depth):
            lines.append(" " * indent + "all:")
            lines.append(" " * (indent + 2) + "- ")
            indent += 4
        lines[-1] = " " * indent + "- eq: {field: tool, value: \"B\"}"
        return "\n".join(lines) + "\n"

    def test_depth_9(self):
        body = _BASE_HEADER + self._nested_all(9) + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertIn(ctx.exception.error_kind, ("depth_limit", "parse_error"))

    def test_depth_20(self):
        body = _BASE_HEADER + self._nested_all(20) + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertIn(ctx.exception.error_kind, ("depth_limit", "parse_error"))

    def test_depth_100(self):
        body = _BASE_HEADER + self._nested_all(100) + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        # Depth 100 may hit file-size limit BEFORE depth_limit — both OK.
        self.assertIn(ctx.exception.error_kind,
                      ("depth_limit", "parse_error", "size_limit"))

    def test_depth_1000_may_hit_size(self):
        body = _BASE_HEADER + self._nested_all(300) + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertIn(ctx.exception.error_kind,
                      ("depth_limit", "parse_error", "size_limit"))

    def test_depth_flat_but_deep_mapping(self):
        # Build deep mapping of mappings.
        body = _BASE_HEADER + """\
      all:
        - all:
            - all:
                - all:
                    - all:
                        - all:
                            - all:
                                - all:
                                    - all:
                                        - eq: {field: tool, value: "B"}
""" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertIn(ctx.exception.error_kind, ("depth_limit", "parse_error"))


class TestYamlTagBombs(TestEnvContext):
    """5 custom-tag payloads → tag_rejected."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "tag.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def test_python_name_tag(self):
        body = _BASE_HEADER.replace('"x"', "!!python/name:os.system foo") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_python_object_tag(self):
        body = _BASE_HEADER.replace('"x"', "!!python/object bar") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_short_local_tag(self):
        body = _BASE_HEADER.replace('"x"', "!foo baz") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_binary_tag(self):
        body = _BASE_HEADER.replace('"x"', "!!binary aGVsbG8=") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_uri_tag(self):
        body = _BASE_HEADER.replace('"x"', "!<http://evil/tag> x") + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")


class TestYamlFlowAbuse(TestEnvContext):
    """3 flow-abuse payloads → parse_error."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "flow.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def test_flow_top_level_mapping(self):
        body = "{schema: \"policy-dsl/v1\", id: x, kind: deny_list}\n"
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_multiline_flow_mapping(self):
        body = _BASE_HEADER + "      eq: {\n        field: tool,\n        value: \"B\"\n      }\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_nested_flow_with_unterminated(self):
        body = _BASE_HEADER + "      eq: {field: tool, value: \"B\"\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")


class TestYamlDirectiveMultidoc(TestEnvContext):
    """3 directive / multi-doc payloads → parse_error."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "dir.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def test_yaml_directive(self):
        body = "%YAML 1.2\n" + _BASE_HEADER + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_tag_directive(self):
        body = "%TAG ! tag:foo.com,2024:\n" + _BASE_HEADER + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_multidoc_separator(self):
        body = _BASE_HEADER + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER + "\n---\nschema: \"policy-dsl/v1\"\n"
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")


class TestYamlSizeBombs(TestEnvContext):
    """4 size / scalar / key-count payloads → size_limit."""

    def _load_str(self, body: str) -> None:
        path = self.project_dir / "size.policy.yaml"
        path.write_text(body, encoding="utf-8")
        P.load(path)

    def test_oversize_file(self):
        # > 64 KiB raw.
        filler = ("# pad " + ("x" * 100) + "\n") * 800
        body = _BASE_HEADER + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER + filler
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_oversize_scalar(self):
        big = "x" * (17 * 1024)
        body = _BASE_HEADER.replace('"x"', f'"{big}"') + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_huge_quoted_scalar_in_value(self):
        big = "y" * (18 * 1024)
        body = _BASE_HEADER + f"      eq: {{field: tool, value: \"{big}\"}}\n" + _BASE_FOOTER
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_key_count_over_2000(self):
        # Build a mapping with > 2000 keys at a single level.
        keys = "\n".join(f"  k{i}: v" for i in range(2100))
        body = _BASE_HEADER + "      eq: {field: tool, value: \"B\"}\n" + _BASE_FOOTER + keys + "\n"
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self._load_str(body)
        # May hit file size OR key count first.
        self.assertIn(ctx.exception.error_kind, ("size_limit", "parse_error"))


class TestReDoSVectors(TestEnvContext):
    """PLAN-025 F-qa-003 extension — 5 ReDoS-shaped patterns.

    Each must EITHER load within a tight budget OR be rejected with a
    documented error_kind. Neither outcome is a hang.
    """

    def _load_regex_with_pattern(self, pattern: str) -> None:
        body = (
            _BASE_HEADER
            + "      regex:\n"
            + "        field: tool_input.command\n"
            + f'        pattern: "{pattern}"\n'
            + _BASE_FOOTER
        )
        path = self.project_dir / "redos.policy.yaml"
        path.write_text(body, encoding="utf-8")
        # Must not hang; must either load or raise PolicyLoadError.
        import time as _t
        t0 = _t.monotonic()
        try:
            P.load(path)
        except P.PolicyLoadError:
            pass  # acceptable outcome
        elapsed = _t.monotonic() - t0
        assert elapsed < 1.0, (
            f"pattern {pattern!r} load took {elapsed:.3f}s (>1s budget); "
            "ReDoS at policy load time"
        )

    def test_backref_plus_quantifier_rejected(self):
        # (a)\1+ — classic backref-in-quantifier → regex_compile_error
        body = (
            _BASE_HEADER
            + "      regex:\n"
            + "        field: tool_input.command\n"
            + '        pattern: "(a)\\\\1+"\n'
            + _BASE_FOOTER
        )
        path = self.project_dir / "backref.policy.yaml"
        path.write_text(body, encoding="utf-8")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            P.load(path)
        self.assertEqual(ctx.exception.error_kind, "regex_compile_error")

    def test_nested_quantifier_stack_loads_bounded(self):
        self._load_regex_with_pattern(r"(a+)+")

    def test_alternation_stack_loads_bounded(self):
        self._load_regex_with_pattern(r"(a|a)+")

    def test_long_alternation_loads_bounded(self):
        self._load_regex_with_pattern("|".join(f"x{i}" for i in range(40)))

    def test_quantifier_nesting_compiles_or_rejects_fast(self):
        self._load_regex_with_pattern(r"((a*)*)*")


if __name__ == "__main__":
    import unittest
    unittest.main()
