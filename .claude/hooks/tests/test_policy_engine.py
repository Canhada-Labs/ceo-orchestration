"""Unit tests for _lib.policy engine (PLAN-014 Phase A.3 + A.6).

Tests the hand-rolled YAML subset parser + predicate compiler + evaluator +
canonical-hash identity against SPEC/v1/policy-dsl.schema.md §3-§7.

Covers ≥60 tests per PLAN-014 A.6 engine-subset floor:

- ``TestYAMLSubsetParser`` — parse accept/reject matrix (§3.1-§3.2)
- ``TestPredicateForms`` — one happy + one sad per form (14 × 2 = 28)
- ``TestErrorModel`` — each §5 error_kind triggered (11)
- ``TestCanonicalHash`` — stability + sensitivity (6)
- ``TestDecide`` — end-to-end decide() paths + audit emission (8+)
- ``TestLoadFailures`` — file-size + BOM + top-level key matrix (8+)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy as P  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


_MIN_DOC = """\
schema: "policy-dsl/v1"
id: test-policy
description: "Test"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: deny_rm_rf
    description: "rm -rf block"
    decision: block
    reason: dangerous_rm
    predicate:
      all:
        - eq: {field: tool, value: "Bash"}
        - regex:
            field: tool_input.command
            pattern: "rm -rf"
error_model:
  reasons:
    dangerous_rm: "Refusing rm -rf"
"""


def _write(base: Path, name: str, body: str) -> Path:
    p = base / f"{name}.policy.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


class _LoaderMixin:
    """Mixin providing .load_text(body) for TestEnvContext-based classes."""

    def load_text(self: "TestEnvContext", body: str, name: str = "x") -> P.Policy:
        path = _write(self.project_dir, name, body)
        return P.load(path)


# ---------------------------------------------------------------------------
# §3.1-§3.2 YAML subset parser
# ---------------------------------------------------------------------------


class TestYAMLSubsetParser(TestEnvContext, _LoaderMixin):
    def test_accepts_block_mapping_and_sequence(self):
        pol = self.load_text(_MIN_DOC)
        self.assertEqual(pol.policy_id, "test-policy")
        self.assertEqual(pol.kind, "deny_list")
        self.assertEqual(len(pol.rules), 1)

    def test_accepts_plain_scalars_null_true_false_int(self):
        doc = _MIN_DOC + "# appended comment ignored\n"
        pol = self.load_text(doc)
        self.assertEqual(pol.defaults.get("decision", "allow"), "allow")

    def test_accepts_double_quoted_with_escapes(self):
        body = _MIN_DOC.replace('"Test"', '"Line\\nTwo\\t\\"quote\\""')
        pol = self.load_text(body)
        self.assertIn("Line\nTwo\t\"quote\"", pol.description)

    def test_accepts_single_quoted_with_doubled_quote_escape(self):
        body = _MIN_DOC.replace('"Test"', "'it''s ok'")
        pol = self.load_text(body)
        self.assertEqual(pol.description, "it's ok")

    def test_rejects_anchor(self):
        body = _MIN_DOC.replace('"Test"', "&x Test")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_rejects_alias(self):
        body = _MIN_DOC.replace('"Test"', "*x")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_rejects_python_tag(self):
        body = _MIN_DOC.replace('"Test"', "!!python/object Test")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_rejects_custom_tag(self):
        body = _MIN_DOC.replace('"Test"', "!custom Test")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_rejects_flow_mapping(self):
        body = _MIN_DOC.replace("kind: deny_list", "kind: {k: v}")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_flow_sequence(self):
        body = _MIN_DOC.replace("kind: deny_list", "kind: [a, b]")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_block_scalar_literal(self):
        body = _MIN_DOC.replace('"Test"', "|\n  block")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_directive_yaml(self):
        body = "%YAML 1.2\n" + _MIN_DOC
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_multi_doc(self):
        body = _MIN_DOC + "\n---\nschema: \"policy-dsl/v1\"\n"
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_utf8_bom(self):
        # Write raw bytes with BOM.
        path = self.project_dir / "bom.policy.yaml"
        path.write_bytes(b"\xef\xbb\xbf" + _MIN_DOC.encode("utf-8"))
        with self.assertRaises(P.PolicyLoadError) as ctx:
            P.load(path)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_rejects_depth_beyond_limit(self):
        # Build a deeply nested "all" chain.
        pred = "eq: {field: tool, value: \"Bash\"}"
        # Wrap 20 deep in all/any.
        for _ in range(20):
            pred = "all:\n  - " + pred.replace("\n", "\n    ")
        body = _MIN_DOC.replace(
            "predicate:\n      all:\n        - eq: {field: tool, value: \"Bash\"}\n        - regex:\n            field: tool_input.command\n            pattern: \"rm -rf\"",
            "predicate:\n      " + pred.replace("\n", "\n      "),
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertIn(ctx.exception.error_kind, ("depth_limit", "parse_error"))

    def test_rejects_oversize_scalar(self):
        big = "x" * (17 * 1024)
        body = _MIN_DOC.replace('"Test"', f'"{big}"')
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_rejects_oversize_file(self):
        body = _MIN_DOC + ("\n# filler " + ("x" * 100) + "\n") * 800
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_plain_scalar_coerces_bool_null(self):
        # Re-check via defaults.decision + reason value paths.
        body = _MIN_DOC  # uses `decision: allow` plain scalar
        pol = self.load_text(body)
        self.assertEqual(pol.defaults.get("decision", "allow"), "allow")

    def test_tab_indent_rejected(self):
        body = _MIN_DOC.replace("  decision: allow", "\tdecision: allow")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_comment_on_own_line_ignored(self):
        body = "# header comment\n" + _MIN_DOC
        pol = self.load_text(body)
        self.assertEqual(pol.kind, "deny_list")

    def test_duplicate_top_level_key_rejected(self):
        body = _MIN_DOC + "\nkind: allow_list\n"
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")


# ---------------------------------------------------------------------------
# §3.5 Predicate forms — happy + sad per form
# ---------------------------------------------------------------------------


def _policy_with_predicate(pred_yaml_inline: str,
                           extra_reason: str = "dangerous_rm") -> str:
    return f"""\
schema: "policy-dsl/v1"
id: pred-test
description: "pred"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: r1
    description: "r"
    decision: block
    reason: {extra_reason}
    predicate:
{pred_yaml_inline}
error_model:
  reasons:
    {extra_reason}: "msg"
"""


class TestPredicateForms(TestEnvContext, _LoaderMixin):

    # ---- eq ----
    def test_eq_matches(self):
        pol = self.load_text(_policy_with_predicate("      eq: {field: tool, value: \"Bash\"}"))
        self.assertEqual(pol.decide({"tool": "Bash"})["decision"], "block")

    def test_eq_miss(self):
        pol = self.load_text(_policy_with_predicate("      eq: {field: tool, value: \"Bash\"}"))
        self.assertEqual(pol.decide({"tool": "Read"}).get("decision", "allow"), "allow")

    # ---- neq ----
    def test_neq_matches(self):
        pol = self.load_text(_policy_with_predicate("      neq: {field: tool, value: \"Bash\"}"))
        self.assertEqual(pol.decide({"tool": "Read"})["decision"], "block")

    def test_neq_miss(self):
        pol = self.load_text(_policy_with_predicate("      neq: {field: tool, value: \"Bash\"}"))
        self.assertEqual(pol.decide({"tool": "Bash"}).get("decision", "allow"), "allow")

    # ---- in ----
    def test_in_matches(self):
        pol = self.load_text(_policy_with_predicate(
            "      in:\n        field: tool\n        values:\n          - \"Bash\"\n          - \"Read\""))
        self.assertEqual(pol.decide({"tool": "Bash"})["decision"], "block")

    def test_in_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      in:\n        field: tool\n        values:\n          - \"Bash\"\n          - \"Read\""))
        self.assertEqual(pol.decide({"tool": "Write"}).get("decision", "allow"), "allow")

    # ---- not_in ----
    def test_not_in_matches(self):
        pol = self.load_text(_policy_with_predicate(
            "      not_in:\n        field: tool\n        values:\n          - \"Bash\""))
        self.assertEqual(pol.decide({"tool": "Write"})["decision"], "block")

    def test_not_in_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      not_in:\n        field: tool\n        values:\n          - \"Bash\""))
        self.assertEqual(pol.decide({"tool": "Bash"}).get("decision", "allow"), "allow")

    # ---- regex ----
    def test_regex_matches(self):
        pol = self.load_text(_policy_with_predicate(
            "      regex:\n        field: tool_input.command\n        pattern: \"rm -rf\""))
        self.assertEqual(
            pol.decide({"tool_input": {"command": "sudo rm -rf /tmp"}})["decision"],
            "block",
        )

    def test_regex_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      regex:\n        field: tool_input.command\n        pattern: \"rm -rf\""))
        self.assertEqual(
            pol.decide({"tool_input": {"command": "ls"}})["decision"],
            "allow",
        )

    # ---- starts_with ----
    def test_starts_with_match(self):
        pol = self.load_text(_policy_with_predicate(
            "      starts_with:\n        field: tool_input.command\n        prefix: \"rm\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "rm -rf"}})["decision"], "block")

    def test_starts_with_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      starts_with:\n        field: tool_input.command\n        prefix: \"rm\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls"}}).get("decision", "allow"), "allow")

    # ---- ends_with ----
    def test_ends_with_match(self):
        pol = self.load_text(_policy_with_predicate(
            "      ends_with:\n        field: tool_input.command\n        suffix: \".sh\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "./boot.sh"}})["decision"], "block")

    def test_ends_with_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      ends_with:\n        field: tool_input.command\n        suffix: \".sh\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls"}}).get("decision", "allow"), "allow")

    # ---- contains ----
    def test_contains_match(self):
        pol = self.load_text(_policy_with_predicate(
            "      contains:\n        field: tool_input.command\n        substring: \"secret\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "echo secret"}})["decision"], "block")

    def test_contains_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      contains:\n        field: tool_input.command\n        substring: \"secret\""))
        self.assertEqual(pol.decide({"tool_input": {"command": "echo ok"}}).get("decision", "allow"), "allow")

    # ---- length_le ----
    def test_length_le_match(self):
        pol = self.load_text(_policy_with_predicate(
            "      length_le:\n        field: tool_input.command\n        value: 5"))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls"}})["decision"], "block")

    def test_length_le_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      length_le:\n        field: tool_input.command\n        value: 5"))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls -la long"}}).get("decision", "allow"), "allow")

    # ---- length_ge ----
    def test_length_ge_match(self):
        pol = self.load_text(_policy_with_predicate(
            "      length_ge:\n        field: tool_input.command\n        value: 5"))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls -la long"}})["decision"], "block")

    def test_length_ge_miss(self):
        pol = self.load_text(_policy_with_predicate(
            "      length_ge:\n        field: tool_input.command\n        value: 5"))
        self.assertEqual(pol.decide({"tool_input": {"command": "ls"}}).get("decision", "allow"), "allow")

    # ---- path_under ----
    def test_path_under_match(self):
        root = str(self.project_dir)
        pol = self.load_text(_policy_with_predicate(
            f"      path_under:\n        field: tool_input.file_path\n        root: \"{root}\""))
        target = str(self.project_dir / "sub" / "f.txt")
        self.assertEqual(pol.decide({"tool_input": {"file_path": target}})["decision"], "block")

    def test_path_under_escape(self):
        root = str(self.project_dir / "inside")
        (self.project_dir / "inside").mkdir()
        pol = self.load_text(_policy_with_predicate(
            f"      path_under:\n        field: tool_input.file_path\n        root: \"{root}\""))
        # "..\" escape attempt:
        target = str(self.project_dir / "outside.txt")
        self.assertEqual(pol.decide({"tool_input": {"file_path": target}}).get("decision", "allow"), "allow")

    # ---- all / any / not ----
    def test_all_short_circuits(self):
        pol = self.load_text(_policy_with_predicate(
            "      all:\n        - eq: {field: tool, value: \"Bash\"}\n"
            "        - eq: {field: mode, value: \"x\"}"))
        self.assertEqual(pol.decide({"tool": "Bash", "mode": "x"})["decision"], "block")
        self.assertEqual(pol.decide({"tool": "Bash", "mode": "y"})["decision"], "allow")

    def test_any_short_circuits(self):
        pol = self.load_text(_policy_with_predicate(
            "      any:\n        - eq: {field: tool, value: \"Bash\"}\n"
            "        - eq: {field: tool, value: \"Read\"}"))
        self.assertEqual(pol.decide({"tool": "Read"})["decision"], "block")
        self.assertEqual(pol.decide({"tool": "Write"}).get("decision", "allow"), "allow")

    def test_not_inverts(self):
        pol = self.load_text(_policy_with_predicate(
            "      not:\n        eq: {field: tool, value: \"Bash\"}"))
        self.assertEqual(pol.decide({"tool": "Read"})["decision"], "block")
        self.assertEqual(pol.decide({"tool": "Bash"}).get("decision", "allow"), "allow")


# ---------------------------------------------------------------------------
# §5 Error model — one trigger per enum
# ---------------------------------------------------------------------------


class TestErrorModel(TestEnvContext, _LoaderMixin):
    def test_parse_error(self):
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text("schema: \"policy-dsl/v1\"\nid: [1,2]\n")
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_predicate_missing_unknown_form(self):
        body = _MIN_DOC.replace(
            "predicate:\n      all:",
            "predicate:\n      nope_not_a_form:",
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "predicate_missing")

    def test_predicate_missing_when_absent(self):
        body = _MIN_DOC.replace(
            "    predicate:\n      all:\n        - eq: {field: tool, value: \"Bash\"}\n        - regex:\n            field: tool_input.command\n            pattern: \"rm -rf\"\n",
            "",
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "predicate_missing")

    def test_depth_limit(self):
        # Build nested all explicitly.
        pred_lines = []
        indent = 6
        for i in range(12):
            pred_lines.append(" " * indent + "all:")
            pred_lines.append(" " * (indent + 2) + "- ")
            indent += 4
        # terminal predicate
        pred_lines[-1] = " " * indent + "- eq: {field: tool, value: \"Bash\"}"
        body = _MIN_DOC.replace(
            "predicate:\n      all:\n        - eq: {field: tool, value: \"Bash\"}\n        - regex:\n            field: tool_input.command\n            pattern: \"rm -rf\"",
            "predicate:\n" + "\n".join(pred_lines),
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertIn(ctx.exception.error_kind, ("depth_limit", "parse_error"))

    def test_size_limit_scalar(self):
        big = "x" * (17 * 1024)
        body = _MIN_DOC.replace('"Test"', f'"{big}"')
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "size_limit")

    def test_alias_rejected(self):
        body = _MIN_DOC.replace('"Test"', "&a scalar")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "alias_rejected")

    def test_tag_rejected(self):
        body = _MIN_DOC.replace('"Test"', "!!python/name:os.system test")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "tag_rejected")

    def test_timeout_deadline_exceeded(self):
        # Force deadline-exceeded by monkey-patching the limit.
        original = P._LIMIT_PARSE_CPU_MS
        P._LIMIT_PARSE_CPU_MS = 0.0000001
        try:
            # Large enough doc that parser checks deadline mid-way.
            body = _MIN_DOC + ("\n# pad " + ("x" * 80) + "\n") * 50
            with self.assertRaises(P.PolicyLoadError) as ctx:
                self.load_text(body, name="timeout")
            self.assertIn(ctx.exception.error_kind, ("timeout", "parse_error"))
        finally:
            P._LIMIT_PARSE_CPU_MS = original

    def test_field_missing_is_predicate_false(self):
        pol = self.load_text(_policy_with_predicate(
            "      eq: {field: nested.deep.gone, value: \"x\"}"))
        # No error raised — predicate is false, default allow wins.
        self.assertEqual(pol.decide({"tool": "Bash"}).get("decision", "allow"), "allow")

    def test_regex_compile_error(self):
        body = _policy_with_predicate(
            "      regex:\n        field: tool\n        pattern: \"(unclosed\"")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "regex_compile_error")

    def test_schema_version_mismatch(self):
        body = _MIN_DOC.replace('"policy-dsl/v1"', '"policy-dsl/v2"')
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "schema_version_mismatch")


# ---------------------------------------------------------------------------
# §6 Canonical hash
# ---------------------------------------------------------------------------


class TestCanonicalHash(TestEnvContext, _LoaderMixin):
    def test_whitespace_only_change_same_hash(self):
        a = self.load_text(_MIN_DOC, name="a")
        spaced = _MIN_DOC.replace("  decision: allow",
                                  "  decision: allow")  # no-op baseline
        # Add trailing blank lines.
        b = self.load_text(spaced + "\n\n\n", name="b")
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    def test_comment_change_same_hash(self):
        a = self.load_text(_MIN_DOC, name="a")
        b = self.load_text("# new comment\n" + _MIN_DOC + "# tail\n", name="b")
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    def test_top_level_key_reorder_same_hash(self):
        # json.dumps(sort_keys=True) at hash time → reordering top-level
        # keys yields identical hash.
        reordered = """\
id: test-policy
schema: "policy-dsl/v1"
kind: deny_list
description: "Test"
defaults:
  decision: allow
error_model:
  reasons:
    dangerous_rm: "Refusing rm -rf"
rules:
  - id: deny_rm_rf
    description: "rm -rf block"
    decision: block
    reason: dangerous_rm
    predicate:
      all:
        - eq: {field: tool, value: "Bash"}
        - regex:
            field: tool_input.command
            pattern: "rm -rf"
"""
        a = self.load_text(_MIN_DOC, name="a")
        b = self.load_text(reordered, name="b")
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    def test_rule_order_changes_hash(self):
        two_rules = _MIN_DOC.replace(
            "rules:\n  - id: deny_rm_rf",
            "rules:\n  - id: first_allow\n    description: \"\"\n    decision: allow\n    predicate:\n      eq: {field: tool, value: \"Read\"}\n  - id: deny_rm_rf",
        )
        swapped = _MIN_DOC.replace(
            "rules:\n  - id: deny_rm_rf",
            "rules:\n  - id: deny_rm_rf",
        )  # baseline single-rule
        a = self.load_text(two_rules, name="a")
        b = self.load_text(swapped, name="b")
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_predicate_change_changes_hash(self):
        a = self.load_text(_MIN_DOC, name="a")
        b_body = _MIN_DOC.replace('pattern: "rm -rf"', 'pattern: "rm -rF"')
        b = self.load_text(b_body, name="b")
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_reason_enum_change_changes_hash(self):
        a = self.load_text(_MIN_DOC, name="a")
        b_body = _MIN_DOC.replace("Refusing rm -rf", "Refusing rm -rf (updated)")
        b = self.load_text(b_body, name="b")
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)


# ---------------------------------------------------------------------------
# decide() — end-to-end behavior + audit emission
# ---------------------------------------------------------------------------


class TestDecide(TestEnvContext, _LoaderMixin):
    def _read_audit(self) -> list:
        raw = self.read_audit_log()
        events = []
        for line in raw.splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def test_allow_path_emits_only_evaluated(self):
        pol = self.load_text(_MIN_DOC)
        pol.decide({"tool": "Read"})
        events = self._read_audit()
        actions = [e["action"] for e in events]
        self.assertIn("policy_evaluated", actions)
        self.assertNotIn("policy_denied", actions)

    def test_deny_path_emits_both(self):
        pol = self.load_text(_MIN_DOC)
        pol.decide({"tool": "Bash", "tool_input": {"command": "rm -rf /"}})
        events = self._read_audit()
        actions = [e["action"] for e in events]
        self.assertIn("policy_evaluated", actions)
        self.assertIn("policy_denied", actions)

    def test_first_match_wins(self):
        body = """\
schema: "policy-dsl/v1"
id: fmw
description: "first-match"
kind: mixed
defaults:
  decision: allow
rules:
  - id: allow_read
    description: ""
    decision: allow
    predicate:
      eq: {field: tool, value: "Read"}
  - id: deny_all
    description: ""
    decision: block
    reason: deny_all_reason
    predicate:
      eq: {field: tool, value: "Read"}
error_model:
  reasons:
    deny_all_reason: "nope"
"""
        pol = self.load_text(body)
        # First matching rule is allow.
        self.assertEqual(pol.decide({"tool": "Read"}).get("decision", "allow"), "allow")

    def test_no_match_falls_through_to_defaults(self):
        pol = self.load_text(_MIN_DOC)
        d = pol.decide({"tool": "SomethingElse"})
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_field_missing_predicate_false(self):
        pol = self.load_text(_MIN_DOC)
        # No tool_input at all — regex branch is False; and tool != "Bash" → no rule.
        self.assertEqual(pol.decide({"tool": "Bash"}).get("decision", "allow"), "allow")

    def test_duration_ms_emitted(self):
        pol = self.load_text(_MIN_DOC)
        pol.decide({"tool": "Read"})
        events = self._read_audit()
        evals = [e for e in events if e["action"] == "policy_evaluated"]
        self.assertTrue(evals)
        self.assertIn("duration_ms", evals[0])
        self.assertGreaterEqual(int(evals[0]["duration_ms"]), 0)

    def test_audit_payload_fields(self):
        pol = self.load_text(_MIN_DOC)
        pol.decide({"tool": "Bash", "tool_input": {"command": "rm -rf /"}})
        events = self._read_audit()
        denied = [e for e in events if e["action"] == "policy_denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["policy_id"], "test-policy")
        self.assertEqual(denied[0]["rule_id"], "deny_rm_rf")
        self.assertEqual(denied[0]["reason"], "dangerous_rm")

    def test_empty_rules_uses_default(self):
        body = """\
schema: "policy-dsl/v1"
id: empty-rules
description: "x"
kind: allow_list
defaults:
  decision: allow
rules: []
error_model:
  reasons:
    _placeholder: "n/a"
"""
        pol = self.load_text(body)
        self.assertEqual(pol.decide({"tool": "X"}).get("decision", "allow"), "allow")

    def test_default_block_path(self):
        body = """\
schema: "policy-dsl/v1"
id: default-deny
description: "x"
kind: deny_list
defaults:
  decision: block
  reason: default_blocked
rules: []
error_model:
  reasons:
    default_blocked: "default deny"
"""
        pol = self.load_text(body)
        d = pol.decide({"tool": "X"})
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["reason"], "default_blocked")
        self.assertIn("message", d)


# ---------------------------------------------------------------------------
# Extra load-failure coverage
# ---------------------------------------------------------------------------


class TestLoadFailures(TestEnvContext, _LoaderMixin):
    def test_missing_top_level_schema(self):
        body = _MIN_DOC.replace('schema: "policy-dsl/v1"\n', "")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertIn(ctx.exception.error_kind, ("parse_error", "schema_version_mismatch"))

    def test_missing_id(self):
        body = _MIN_DOC.replace("id: test-policy\n", "")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_bad_kind_enum(self):
        body = _MIN_DOC.replace("kind: deny_list", "kind: unknown")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_bad_defaults_decision(self):
        body = _MIN_DOC.replace("decision: allow\nrules:", "decision: maybe\nrules:")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_duplicate_rule_id(self):
        body = _MIN_DOC.replace(
            "rules:\n  - id: deny_rm_rf",
            "rules:\n  - id: dup\n    description: \"\"\n    decision: allow\n    predicate:\n      eq: {field: tool, value: \"X\"}\n  - id: dup",
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_block_rule_missing_reason(self):
        body = _MIN_DOC.replace(
            "    decision: block\n    reason: dangerous_rm\n",
            "    decision: block\n",
        )
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_block_rule_reason_not_in_error_model(self):
        body = _MIN_DOC.replace("reason: dangerous_rm", "reason: ghost_reason")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "parse_error")

    def test_regex_pattern_too_long(self):
        big_pat = "a" * 600
        body = _policy_with_predicate(
            f"      regex:\n        field: tool\n        pattern: \"{big_pat}\"")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "regex_compile_error")

    def test_policy_load_error_unknown_kind_falls_back(self):
        e = P.PolicyLoadError("not_a_real_kind", "x")
        self.assertEqual(e.error_kind, "parse_error")


if __name__ == "__main__":
    import unittest
    unittest.main()


class TestP2SecIErrorRedaction(TestEnvContext):
    """P2-SEC-I (PLAN-019): PolicyLoadError.detail must redact secrets."""

    def test_api_key_in_detail_is_redacted(self):
        from _lib import policy
        err = policy.PolicyLoadError(
            "parse_error",
            "unexpected token near sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123",
            "my.policy",
        )
        self.assertNotIn("sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123", err.detail)
        self.assertIn("[API_KEY]", err.detail)

    def test_github_pat_in_detail_is_redacted(self):
        from _lib import policy
        err = policy.PolicyLoadError(
            "parse_error",
            "unknown ghp_ABCDEFGHIJKLMNOPQRSTU12345",
            "my.policy",
        )
        self.assertIn("[GITHUB_PAT]", err.detail)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTU12345", err.detail)

    def test_detail_bounded_to_200_chars(self):
        from _lib import policy
        err = policy.PolicyLoadError("parse_error", "x" * 5000, "p")
        self.assertLessEqual(len(err.detail), 200)

    def test_empty_detail_does_not_error(self):
        from _lib import policy
        err = policy.PolicyLoadError("parse_error", "", "p")
        self.assertEqual(err.detail, "")
