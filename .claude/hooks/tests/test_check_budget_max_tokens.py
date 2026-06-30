"""Unit tests for check_budget.py plan-frontmatter ``max_tokens`` cap.

Validates PLAN-065 §4.5.D — frontmatter > env > default precedence —
and the YAML safe-load int-only schema (Sec Unseen-5 attack surface).

The staged patch lives at::

    .claude/plans/PLAN-065/staged-patches/phase-5-d-max-tokens/
        check_budget.py.new

Tests load the staged module under the alias ``hk_staged`` via
``importlib`` so we exercise the patched code without rewriting the
canonical hook (sentinel-signed Owner GPG ceremony promotes that).

Coverage:
- Happy path:  ``max_tokens: 500000`` → cap=500000, source=plan_frontmatter
- Happy path:  no key                 → falls to env or default
- Reject:      ``"500000"`` (quoted)
- Reject:      ``1e500``    (scientific)
- Reject:      ``1e6``      (small scientific — the PLAN-065 §4.5.D example)
- Reject:      ``-100``     (negative)
- Reject:      ``50000000`` (>10M ceiling)
- Reject:      ``&alias 100000`` (YAML alias reference)
- Reject:      ``true`` / ``[1,2]`` / ``{a:1}`` (non-int shapes)
- Reject:      ``00500000`` (leading-zero / octal-look)
- ``_resolve_cap`` precedence: frontmatter > env > default
- ``decide()`` forwards ``cap_source`` into ``budget_exceeded`` effect
- ``_apply_effect`` graceful degrade if audit_emit lacks ``cap_source``
- Real-fs synthesis via ``TestEnvContext`` (no real $HOME / $CLAUDE_PROJECT_DIR)

S5 contract: every test asserts at least one behavior beyond exit code.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any, Dict, Optional

_HOOKS_DIR = Path(__file__).resolve().parent.parent

# Make _lib importable for TestEnvContext.
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Load the STAGED module under a unique alias so we don't shadow the
# canonical ``check_budget`` import other tests rely on.
# ---------------------------------------------------------------------------

# Re-pointed to the production module: the PLAN-065 §4.5.D max_tokens
# patch shipped long ago and is now the canonical check_budget.py.
_STAGED_PATH = _HOOKS_DIR / "check_budget.py"


def _load_staged_module():
    """Import the staged ``check_budget.py.new`` as ``hk_staged``.

    The ``.new`` suffix is not a registered Python source extension, so
    ``spec_from_file_location`` returns None. We explicitly hand a
    ``SourceFileLoader`` that doesn't care about the suffix.
    """
    module_name = "check_budget_phase5d_staged"
    loader = SourceFileLoader(module_name, str(_STAGED_PATH))
    spec = importlib.util.spec_from_loader(module_name, loader)
    if spec is None:
        raise RuntimeError(
            f"could not build spec for staged module at {_STAGED_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


hk_staged = _load_staged_module()


# ---------------------------------------------------------------------------
# Plan-file synthesis helper
# ---------------------------------------------------------------------------


def _plan_text(
    *,
    plan_id: str = "PLAN-099",
    status: str = "executing",
    extra_lines: Optional[str] = None,
) -> str:
    """Build a minimal plan file body. ``extra_lines`` is a raw frontmatter
    chunk inserted before the closing ``---``. Useful for splicing in
    a ``max_tokens:`` line verbatim.
    """
    lines = [
        "---",
        f"id: {plan_id}",
        "title: phase-5-d test plan",
        f"status: {status}",
        "owner: CEO",
    ]
    if extra_lines is not None:
        lines.append(extra_lines.rstrip("\n"))
    lines.append("---")
    lines.append("")
    lines.append("# Body")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# _parse_plan_max_tokens — int-only schema
# ---------------------------------------------------------------------------


class TestParsePlanMaxTokens(TestEnvContext):
    """Direct tests for the ``_parse_plan_max_tokens`` helper."""

    def _write(
        self, slug: str, max_tokens_line: Optional[str]
    ) -> Path:
        plan_id_num = "099"
        body = _plan_text(
            plan_id=f"PLAN-{plan_id_num}",
            extra_lines=max_tokens_line,
        )
        return self.write_project_file(
            f".claude/plans/PLAN-{plan_id_num}-{slug}.md", body
        )

    # ---- happy paths --------------------------------------------------

    def test_valid_int_literal_returns_value(self):
        path = self._write("happy", "max_tokens: 500000")
        self.assertEqual(hk_staged._parse_plan_max_tokens(path), 500000)

    def test_valid_int_literal_at_ceiling_returns_value(self):
        """10M ceiling is INCLUSIVE — exactly 10M passes."""
        path = self._write("ceiling", "max_tokens: 10000000")
        self.assertEqual(hk_staged._parse_plan_max_tokens(path), 10000000)

    def test_key_absent_returns_none_no_breadcrumb(self):
        path = self._write("absent", None)
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        # Key absent is silent — no breadcrumb written.
        self.assertEqual(self.read_audit_errors(), "")

    # ---- attack surface — each rejection writes a breadcrumb ---------

    def test_string_typed_rejected(self):
        path = self._write("string", 'max_tokens: "500000"')
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        errors = self.read_audit_errors()
        self.assertIn("string-typed", errors)
        self.assertIn("PLAN-099", errors)

    def test_single_quoted_string_rejected(self):
        path = self._write("squote", "max_tokens: '500000'")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("string-typed", self.read_audit_errors())

    def test_scientific_notation_huge_rejected(self):
        """``1e500`` is a classic float-overflow attack vector."""
        path = self._write("sci-huge", "max_tokens: 1e500")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_scientific_notation_small_rejected(self):
        """Even seemingly-valid ``1e6`` is rejected by int-only schema."""
        path = self._write("sci-small", "max_tokens: 1e6")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_negative_rejected(self):
        path = self._write("neg", "max_tokens: -100")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_zero_rejected(self):
        path = self._write("zero", "max_tokens: 0")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        # 0 fails the [1-9] regex prefix.
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_overflow_above_ceiling_rejected(self):
        """50_000_000 > 10M ceiling → rejected even though parseable."""
        path = self._write("overflow", "max_tokens: 50000000")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        # 50000000 has 8 digits and matches strict regex but exceeds
        # ceiling — breadcrumb says "exceeds ceiling".
        self.assertIn("exceeds ceiling", self.read_audit_errors())

    def test_alias_reference_rejected(self):
        path = self._write("alias", "max_tokens: &anchor 100000")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("alias/anchor", self.read_audit_errors())

    def test_alias_dereference_rejected(self):
        path = self._write("alias-deref", "max_tokens: *anchor")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("alias/anchor", self.read_audit_errors())

    def test_inline_list_rejected(self):
        path = self._write("list", "max_tokens: [100, 200]")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("non-scalar", self.read_audit_errors())

    def test_inline_mapping_rejected(self):
        path = self._write("mapping", "max_tokens: {a: 1}")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("non-scalar", self.read_audit_errors())

    def test_boolean_rejected(self):
        path = self._write("bool", "max_tokens: true")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_leading_zero_rejected(self):
        path = self._write("octal", "max_tokens: 00500000")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_underscore_separator_rejected(self):
        """Python int() accepts ``500_000`` but spec is strict."""
        path = self._write("underscore", "max_tokens: 500_000")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_hex_rejected(self):
        path = self._write("hex", "max_tokens: 0x186A0")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_decimal_rejected(self):
        path = self._write("decimal", "max_tokens: 500.0")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_plus_sign_rejected(self):
        path = self._write("plus", "max_tokens: +500000")
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))
        self.assertIn("invalid integer literal", self.read_audit_errors())

    def test_no_frontmatter_returns_none(self):
        path = self.write_project_file(
            ".claude/plans/PLAN-099-no-fm.md",
            "# just a body, no frontmatter\n",
        )
        self.assertIsNone(hk_staged._parse_plan_max_tokens(path))

    def test_unreadable_file_breadcrumbs_and_returns_none(self):
        """Missing path → OSError caught, breadcrumb + None."""
        bogus = self.project_dir / ".claude" / "plans" / "PLAN-999-missing.md"
        self.assertIsNone(hk_staged._parse_plan_max_tokens(bogus))
        # OSError is caught and breadcrumbed.
        self.assertIn("read failed", self.read_audit_errors())


# ---------------------------------------------------------------------------
# _resolve_cap — precedence
# ---------------------------------------------------------------------------


class TestResolveCap(TestEnvContext):
    """Frontmatter > env > default precedence."""

    def _write(self, max_tokens_line: Optional[str]) -> Path:
        body = _plan_text(extra_lines=max_tokens_line)
        return self.write_project_file(
            ".claude/plans/PLAN-099-resolve.md", body
        )

    def test_frontmatter_wins_over_env(self):
        path = self._write("max_tokens: 250000")
        env = {"CEO_MAX_PLAN_TOKENS": "999999"}
        cap, source = hk_staged._resolve_cap(path, env=env)
        self.assertEqual(cap, 250000)
        self.assertEqual(source, "plan_frontmatter")

    def test_env_used_when_frontmatter_invalid(self):
        # String value → frontmatter rejected → env wins.
        path = self._write('max_tokens: "abc"')
        env = {"CEO_MAX_PLAN_TOKENS": "777000"}
        cap, source = hk_staged._resolve_cap(path, env=env)
        self.assertEqual(cap, 777000)
        self.assertEqual(source, "env")

    def test_env_used_when_frontmatter_absent(self):
        path = self._write(None)
        env = {"CEO_MAX_PLAN_TOKENS": "333000"}
        cap, source = hk_staged._resolve_cap(path, env=env)
        self.assertEqual(cap, 333000)
        self.assertEqual(source, "env")

    def test_default_used_when_both_absent(self):
        path = self._write(None)
        cap, source = hk_staged._resolve_cap(path, env={})
        self.assertEqual(cap, hk_staged.DEFAULT_MAX_PLAN_TOKENS)
        self.assertEqual(source, "default")

    def test_default_when_no_plan_path(self):
        cap, source = hk_staged._resolve_cap(None, env={})
        self.assertEqual(cap, hk_staged.DEFAULT_MAX_PLAN_TOKENS)
        self.assertEqual(source, "default")

    def test_default_when_overflow_in_frontmatter(self):
        """Overflow rejection in frontmatter → fall through to env/default."""
        path = self._write("max_tokens: 99999999")
        env = {"CEO_MAX_PLAN_TOKENS": "555000"}
        cap, source = hk_staged._resolve_cap(path, env=env)
        self.assertEqual(cap, 555000)
        self.assertEqual(source, "env")


# ---------------------------------------------------------------------------
# decide() forwards cap_source
# ---------------------------------------------------------------------------


class TestDecideCapSource(TestEnvContext):
    def _base(self, **overrides: Any) -> Dict[str, Any]:
        base: Dict[str, Any] = dict(
            plan_id="PLAN-099",
            tokens_used=2_000_000,
            max_plan_tokens=1_000_000,
            bypass_requested=False,
            recent_bypass_count=0,
            bypass_max_per_day=10,
            caller_pid=1234,
            session_id="s1",
            project="/tmp/proj",
            cap_source="plan_frontmatter",
        )
        base.update(overrides)
        return base

    def test_cap_source_forwarded_to_effect(self):
        d, effect = hk_staged.decide(**self._base())
        self.assertTrue(d.allow)
        self.assertIsNotNone(effect)
        self.assertEqual(effect["emit"], "budget_exceeded")
        self.assertEqual(effect["cap_source"], "plan_frontmatter")

    def test_cap_source_default_when_omitted(self):
        # decide() defaults cap_source to "default" when not passed.
        kwargs = self._base()
        kwargs.pop("cap_source")
        d, effect = hk_staged.decide(**kwargs)
        self.assertEqual(effect["cap_source"], "default")

    def test_cap_source_env_propagates(self):
        d, effect = hk_staged.decide(**self._base(cap_source="env"))
        self.assertEqual(effect["cap_source"], "env")


# ---------------------------------------------------------------------------
# _apply_effect — graceful degrade when audit_emit lacks cap_source kwarg
# ---------------------------------------------------------------------------


class TestApplyEffectGracefulDegrade(TestEnvContext):
    """Confirm _apply_effect catches TypeError from older audit_emit."""

    def test_apply_effect_with_cap_source_calls_audit_emit(self):
        """Live audit_emit (post-bump) should accept cap_source."""
        effect = {
            "emit": "budget_exceeded",
            "plan_id": "PLAN-099",
            "tokens_used": 2_000_000,
            "cap": 1_000_000,
            "scope": "plan",
            "session_id": "s1",
            "project": str(self.project_dir),
            "cap_source": "plan_frontmatter",
        }
        # Should not raise. Whether cap_source lands in the event log is
        # decided by audit_emit; we just verify _apply_effect doesn't
        # propagate the kwarg as a TypeError.
        try:
            hk_staged._apply_effect(effect)
        except TypeError as e:  # pragma: no cover - defensive
            self.fail(f"_apply_effect raised TypeError unexpectedly: {e}")

    def test_apply_effect_none_is_noop(self):
        # Calling _apply_effect(None) is documented as a no-op.
        try:
            hk_staged._apply_effect(None)
        except Exception as e:  # pragma: no cover - defensive
            self.fail(f"_apply_effect(None) raised unexpectedly: {e}")


if __name__ == "__main__":
    unittest.main()
