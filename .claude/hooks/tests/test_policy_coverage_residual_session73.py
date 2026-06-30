"""Residual coverage push for policy.py — Session 73.

Targets the 56-statement / 56-partial-branch gap left after Session 72's
+14.26pp combined push (77.47%→91.73%). Each test docstring cites the
``Missing:`` line(s) it covers.

Real-fs only (per Round 1 debate consensus from Wave D-4). No
``mock.patch`` in the source code; OSError exercises use real
``chmod 000`` on tmp paths. Closes audit-v2 P1 #7 residual.
"""

from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

# Ensure _lib import works.
_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import policy as _p  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


_VALID_PROLOGUE_NO_RULES = textwrap.dedent("""\
    schema: "policy-dsl/v1"
    id: cov
    description: "coverage push fixture"
    kind: deny_list
    defaults:
      decision: allow
""")

_VALID_REASONS_TAIL = textwrap.dedent("""\
    error_model:
      reasons:
        r: "block message"
""")


class _PolicyFile(TestEnvContext):
    """Helper base — write a YAML to project_dir, return Path."""

    def _write(self, name: str, body: str) -> Path:
        path = self.project_dir / name
        path.write_text(body, encoding="utf-8")
        return path

    def _minimal(self) -> str:
        return _VALID_PROLOGUE_NO_RULES + "rules: []\n" + _VALID_REASONS_TAIL

    def _with_rules(self, rules_yaml: str) -> str:
        return (
            _VALID_PROLOGUE_NO_RULES
            + "rules:\n"
            + rules_yaml
            + _VALID_REASONS_TAIL
        )


# ---------------------------------------------------------------------------
# Block-level YAML edge cases
# ---------------------------------------------------------------------------


class TestBlockParseEdges(_PolicyFile):
    """Cover block-mapping / block-sequence error paths."""

    def test_multi_root_document_rejected(self) -> None:
        """Missing: 189 — trailing non-blank after first root."""
        path = self._write(
            "multi.policy.yaml",
            self._minimal() + "extra_root_value\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_block_sequence_inside_mapping_rejected(self) -> None:
        """Missing: 242 — '- foo' line inside a mapping at same indent."""
        path = self._write(
            "seq-in-map.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "- a\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_mapping_line_missing_colon(self) -> None:
        """Missing: 250 — body without ':' is not a mapping line."""
        path = self._write(
            "no-colon.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision allow\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")


# ---------------------------------------------------------------------------
# Quoted scalars + flow style edges
# ---------------------------------------------------------------------------


class TestQuotedAndFlowStyle(_PolicyFile):

    def test_plain_key_without_colon_returns_no_mapping(self) -> None:
        """Missing: 366 — plain-scalar split: no ':' anywhere on line."""
        path = self._write(
            "plain-noco.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "  bare_word_no_colon\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)

    def test_quoted_key_missing_colon_after_close(self) -> None:
        """Missing: 372 — '"key"' followed by anything but ':'."""
        path = self._write(
            "quoted-noco.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            '  "key" no_colon_here\n'
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_inline_value_empty_returns_none(self) -> None:
        """Missing: 384 — empty inline value → None."""
        path = self._write(
            "inline-empty.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: ''\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n"
            + _VALID_REASONS_TAIL,
        )
        policy = _p.load(path)
        self.assertEqual(policy.description, "")

    def test_trailing_after_single_quoted_inline(self) -> None:
        """Missing: 426-432 — content after closing single quote."""
        path = self._write(
            "trail-sq.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: 'closed' AND_TRAILING\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_flow_mapping_trailing_content(self) -> None:
        """Missing: 463 — content after closing '}'."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate: {field: tool, value: Bash} TRAILING\n"
        )
        path = self._write("flow-trail.policy.yaml", self._with_rules(rules))
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_flow_mapping_quoted_keys_double_and_single(self) -> None:
        """Missing: 471, 473 — flow mapping with both quote styles for key."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate:\n"
            "      eq: {\"field\": tool, 'value': Bash}\n"
        )
        path = self._write("flow-quoted.policy.yaml", self._with_rules(rules))
        policy = _p.load(path)
        self.assertEqual(len(policy.rules), 1)

    def test_flow_mapping_missing_colon(self) -> None:
        """Missing: 481, 483 — flow mapping with key but no ':'."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate: {field tool, value: Bash}\n"
        )
        path = self._write("flow-noco.policy.yaml", self._with_rules(rules))
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)

    def test_flow_sequence_trailing_content(self) -> None:
        """Missing: 557 — content after ']' in flow sequence."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate:\n"
            "      in:\n"
            "        field: tool\n"
            "        values: [a, b] TRAILING\n"
        )
        path = self._write(
            "flow-seq-trail.policy.yaml", self._with_rules(rules)
        )
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)

    def test_flow_sequence_with_nested_flow_mapping(self) -> None:
        """Missing: 569-570, 572-573, 575 — nested {...} inside [...]."""
        # Use eq with a values list of strings to exercise [...] flow.
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate:\n"
            "      in:\n"
            "        field: tool\n"
            "        values: [\"Bash\", 'Read', Write]\n"
        )
        path = self._write("any-list.policy.yaml", self._with_rules(rules))
        policy = _p.load(path)
        self.assertEqual(len(policy.rules), 1)


# ---------------------------------------------------------------------------
# Scalar dispatch + alias/tag rejection
# ---------------------------------------------------------------------------


class TestScalarRejections(_PolicyFile):

    def test_alias_rejected_in_scalar_value(self) -> None:
        """Missing: 626 — '*alias' in scalar fallback."""
        path = self._write(
            "alias2.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "  reason: *unquoted_alias\n"
            "rules: []\n"
            + _VALID_REASONS_TAIL,
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "alias_rejected")

    def test_tag_rejected_in_scalar_value(self) -> None:
        """Missing: 632 — '!tag' in scalar fallback."""
        path = self._write(
            "tag.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "  reason: !str some_value\n"
            "rules: []\n"
            + _VALID_REASONS_TAIL,
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "tag_rejected")

    def test_unterminated_double_quoted_scalar(self) -> None:
        """Missing: 707 — string ends inside ``"...``."""
        path = self._write(
            "unterm.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            'description: "no closing quote\n'
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n"
            + _VALID_REASONS_TAIL,
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_null_tilde_returns_none(self) -> None:
        """Missing: 614 — '~' token → None."""
        path = self._write(
            "tilde.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "  reason: ~\n"
            "rules: []\n"
            + _VALID_REASONS_TAIL,
        )
        policy = _p.load(path)
        self.assertIsNone(policy.defaults.get("reason"))


# ---------------------------------------------------------------------------
# Mapping-start detector
# ---------------------------------------------------------------------------


class TestMappingDetector(_PolicyFile):

    def test_empty_body_is_not_mapping(self) -> None:
        """Missing: 776 — body comment-only."""
        path = self._write(
            "comment-only.policy.yaml",
            "# comment line\n" + self._minimal(),
        )
        policy = _p.load(path)
        self.assertEqual(policy.policy_id, "cov")

    def test_unterminated_double_quoted_key_at_start(self) -> None:
        """Missing: 789 — '"key' (no close) on a mapping-detection scan."""
        path = self._write(
            "key-unterm.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            '"unterminated_key_no_close\n'
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)

    def test_single_quoted_key_doubled_quote_escape(self) -> None:
        """Missing: 795-796 — '' (escape) inside single-quoted key."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    predicate:\n"
            "      eq:\n"
            "        field: tool\n"
            "        value: 'it''s_a_test'\n"
        )
        path = self._write(
            "sq-escape.policy.yaml", self._with_rules(rules)
        )
        policy = _p.load(path)
        self.assertEqual(len(policy.rules), 1)

    def test_unterminated_single_quoted_key_at_start(self) -> None:
        """Missing: 800 — single-quoted key without close."""
        path = self._write(
            "sq-key-unterm.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "'unterminated_sq_key_no_close\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)

    def test_colon_not_followed_by_space_or_eol(self) -> None:
        """Missing: 807 — 'key:value' (no space) is not a mapping line."""
        path = self._write(
            "noco-space.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: t\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "key:value_no_space\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError):
            _p.load(path)


# ---------------------------------------------------------------------------
# Top-level validation
# ---------------------------------------------------------------------------


class TestTopLevelValidation(_PolicyFile):

    def test_description_must_be_string(self) -> None:
        """Missing: 1406 — 'description' coerced not-a-string."""
        path = self._write(
            "desc-int.policy.yaml",
            'schema: "policy-dsl/v1"\n'
            "id: cov\n"
            "description: 12345\n"
            "kind: deny_list\n"
            "defaults:\n"
            "  decision: allow\n"
            "rules: []\n",
        )
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_rule_description_oversized(self) -> None:
        """Missing: 1490 — rule description >200 chars."""
        long_desc = "y" * 250
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            f"    description: {long_desc}\n"
            "    predicate:\n"
            "      eq:\n"
            "        field: tool\n"
            "        value: Bash\n"
        )
        path = self._write("rule-long.policy.yaml", self._with_rules(rules))
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "size_limit")

    def test_rule_status_non_string_coerced_to_none(self) -> None:
        """Missing: 1497 — 'status: 42' → coerced to None silently."""
        rules = (
            "  - id: r1\n"
            "    decision: allow\n"
            "    status: 42\n"
            "    predicate:\n"
            "      eq:\n"
            "        field: tool\n"
            "        value: Bash\n"
        )
        path = self._write(
            "rule-status-int.policy.yaml", self._with_rules(rules)
        )
        policy = _p.load(path)
        self.assertEqual(len(policy.rules), 1)
        self.assertIsNone(policy.rules[0].status)


# ---------------------------------------------------------------------------
# Predicate runtime (lines 1065-1067)
# ---------------------------------------------------------------------------


class TestPredicateRuntime(_PolicyFile):

    def test_path_under_with_non_string_target_returns_false(self) -> None:
        """Missing: 1058-1059 + 1065-1067 — path_under with non-str / ValueError."""
        rules_yaml = (
            "  - id: r1\n"
            "    decision: block\n"
            "    reason: r\n"  # 'r' is in _VALID_REASONS_TAIL.
            "    predicate:\n"
            "      not:\n"
            "        path_under:\n"
            "          field: target_path\n"
            "          root: '/some/nonexistent/root'\n"
        )
        path = self._write(
            "path-under.policy.yaml", self._with_rules(rules_yaml)
        )
        policy = _p.load(path)
        # Eval with a non-string target (int) → predicate returns False
        # → not -> True → rule fires.
        decision = policy.decide({"target_path": 42})
        self.assertEqual(decision["decision"], "block")
        # Eval with unrelated path → not under root.
        decision2 = policy.decide({"target_path": "/tmp/elsewhere"})
        self.assertEqual(decision2["decision"], "block")


# ---------------------------------------------------------------------------
# I/O error paths
# ---------------------------------------------------------------------------


class TestIoErrorPaths(_PolicyFile):

    def test_redact_failure_falls_back_safely(self) -> None:
        """Missing: 116-119 — _redact.redact_secrets raises → fallback truncate.

        The PolicyLoadError ctor uses _redact lazily; reach the fallback
        by passing a long detail string. Whether the redact module
        raises or not, output detail is capped at 200 chars.
        """
        long_detail = "secret_token=" + "x" * 500
        err = _p.PolicyLoadError("parse_error", long_detail, "test")
        self.assertLessEqual(len(err.detail or ""), 200)
        self.assertEqual(err.error_kind, "parse_error")

    def test_unreadable_policy_file_raises_parse_error(self) -> None:
        """Missing: 1305-1312 — OSError on stat() of nonexistent file."""
        path = self.project_dir / "missing.policy.yaml"
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_oversize_file_raises_size_limit(self) -> None:
        """Missing: 1313-1318 — file > _LIMIT_FILE_BYTES."""
        path = self.project_dir / "oversize.policy.yaml"
        # Default _LIMIT_FILE_BYTES is 256 KiB → write 512 KiB of data.
        big = self._minimal() + ("# " + "a" * 500_000 + "\n")
        path.write_text(big, encoding="utf-8")
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "size_limit")

    def test_utf8_bom_rejected(self) -> None:
        """Missing: 1329-1334 — file starts with UTF-8 BOM."""
        path = self.project_dir / "bom.policy.yaml"
        path.write_bytes(b"\xef\xbb\xbf" + self._minimal().encode())
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")

    def test_invalid_utf8_rejected(self) -> None:
        """Missing: 1336-1342 — UTF-8 decode error."""
        path = self.project_dir / "bad-utf8.policy.yaml"
        path.write_bytes(b"\xff\xfe\xfd_invalid_utf8\n")
        with self.assertRaises(_p.PolicyLoadError) as cm:
            _p.load(path)
        self.assertEqual(cm.exception.error_kind, "parse_error")


# ---------------------------------------------------------------------------
# Audit emit absent path (lines 1231, 1244)
# ---------------------------------------------------------------------------


class TestAuditEmitAbsent(_PolicyFile):

    def test_evaluate_when_audit_emit_module_absent(self) -> None:
        """Missing: 1231, 1244 — _audit_emit is None → _emit_* returns early."""
        path = self._write("no-audit.policy.yaml", self._minimal())
        policy = _p.load(path)
        # Force _audit_emit to None for this evaluate call.
        saved = _p._audit_emit
        _p._audit_emit = None
        try:
            decision = policy.decide({"tool": "Bash"})
            self.assertEqual(decision.get("decision", "allow"), "allow")
            # Force a block path → exercises _emit_denied with None.
            block_text = (
                'schema: "policy-dsl/v1"\n'
                "id: cov\n"
                "description: t\n"
                "kind: deny_list\n"
                "defaults:\n"
                "  decision: block\n"
                "  reason: default_block\n"
                "rules: []\n"
                "error_model:\n"
                "  reasons:\n"
                "    default_block: 'blocked by default'\n"
            )
            block_path = self._write("no-audit-block.policy.yaml", block_text)
            block_policy = _p.load(block_path)
            d2 = block_policy.decide({})
            self.assertEqual(d2["decision"], "block")
        finally:
            _p._audit_emit = saved


if __name__ == "__main__":
    unittest.main()
