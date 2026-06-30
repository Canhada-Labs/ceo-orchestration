"""test_agent_frontmatter.py — coverage for tier_policy._agent_frontmatter.

Targets the staged module at
``.claude/plans/PLAN-071/staging/tier_policy/_agent_frontmatter.py``.

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1            — local canonical-path list (NOT imported from ``_lib``).
* R-CR Unseen #5   — prototype-pollution keys rejected.
* P1-09            — recursive prototype-pollution check across JSON-literal
                     scalar values; depth + array-len DoS guards apply.
* R-SEC U2         — size + depth caps enforced before parse.
* R-SEC6           — NFKC normalisation of scalar values.
* P0-03            — canonical path list spans the 6 spec VETO floor
                     roles (only 2 of which currently exist on disk)
                     plus 4 legacy non-floor archetypes.

Stdlib-only. Python ≥ 3.9.
"""

from __future__ import annotations

import os
import unicodedata
import unittest
from pathlib import Path

from _lib.tier_policy._agent_frontmatter import (
    FrontmatterError,
    parse_agent_frontmatter,
    _LOCAL_CANONICAL_AGENT_PATHS,
    _PROTOTYPE_POLLUTION_KEYS,
    _check_no_pollution,
)


# ---------------------------------------------------------------------------
# Fixture builders (kept inline — staging dir cannot host a conftest.py).
# ---------------------------------------------------------------------------


def _write(tmp: Path, name: str, body: str) -> Path:
    """Helper: write ``body`` to ``tmp / name`` and return the path."""
    target = tmp / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def _fm(body: str) -> str:
    """Wrap a YAML body in the ``---``/``---`` frontmatter delimiters."""
    return f"---\n{body}\n---\nbody-here\n"


class _FsBase(unittest.TestCase):
    """unittest.TestCase variant with ``self.tmp`` (Path) per test."""

    def setUp(self) -> None:
        super().setUp()
        import tempfile

        self._tmp_dir = tempfile.TemporaryDirectory(prefix="tier-fm-")
        self.tmp = Path(self._tmp_dir.name)

    def tearDown(self) -> None:
        self._tmp_dir.cleanup()
        super().tearDown()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


class TestHappyPath(_FsBase):
    """5 valid frontmatter fixtures — parser returns the expected dict."""

    def test_minimal_name_only(self):
        p = _write(self.tmp, "agent.md", _fm("name: alice"))
        out = parse_agent_frontmatter(p)
        self.assertEqual(out["name"], "alice")

    def test_role_and_model(self):
        body = "name: bob\nrole: staff-backend-engineer\nmodel: claude-sonnet-4-6"
        p = _write(self.tmp, "agent.md", _fm(body))
        out = parse_agent_frontmatter(p)
        self.assertEqual(out["role"], "staff-backend-engineer")
        self.assertEqual(out["model"], "claude-sonnet-4-6")

    def test_block_list_tools(self):
        body = "name: c\ntools:\n  - read\n  - write\n  - bash"
        p = _write(self.tmp, "agent.md", _fm(body))
        out = parse_agent_frontmatter(p)
        self.assertEqual(out["tools"], ["read", "write", "bash"])

    def test_no_frontmatter_returns_empty_dict(self):
        p = _write(self.tmp, "agent.md", "no-frontmatter-body\n")
        out = parse_agent_frontmatter(p)
        self.assertEqual(out, {})

    def test_skill_field_supported(self):
        body = "name: d\nskill: testing-strategy"
        p = _write(self.tmp, "agent.md", _fm(body))
        out = parse_agent_frontmatter(p)
        self.assertEqual(out["skill"], "testing-strategy")


# ---------------------------------------------------------------------------
# Negative cases — security-relevant rejects
# ---------------------------------------------------------------------------


class TestPrototypePollution(_FsBase):
    """R-CR Unseen #5 — refuse JS prototype-pollution keys at top level."""

    def test_proto_top_level_rejected(self):
        body = "name: x\n__proto__: evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_constructor_top_level_rejected(self):
        body = "name: x\nconstructor: evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_prototype_top_level_rejected(self):
        body = "name: x\nprototype: evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_define_getter_rejected(self):
        body = "name: x\n__defineGetter__: evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_pollution_keyset_complete(self):
        """All 5 documented pollution keys are in the rejection set."""
        for k in (
            "__proto__",
            "constructor",
            "prototype",
            "__defineGetter__",
            "__defineSetter__",
        ):
            self.assertIn(k, _PROTOTYPE_POLLUTION_KEYS)


class TestRecursivePrototypePollution(_FsBase):
    """P1-09 — JSON-literal scalars must be walked depth-first.

    Pre-fix: ``tools: {"__proto__": {"x": 1}}`` parsed via ``json.loads``
    bypassed the per-key allowlist. Now ``_coerce_scalar`` calls
    ``_check_no_pollution`` recursively so any pollution key at any
    depth raises ``FrontmatterError``.
    """

    def test_proto_pollution_in_json_literal_scalar(self):
        """P1-09 — flat JSON-literal containing ``__proto__`` rejected."""
        body = 'name: x\ntools: {"__proto__": "evil"}'
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_proto_pollution_at_depth_3(self):
        """P1-09 — pollution key 3 levels deep inside JSON-literal rejected."""
        body = (
            'name: x\n'
            'tools: {"a": {"b": {"__proto__": {"x": 1}}}}'
        )
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_proto_pollution_in_list_value(self):
        """P1-09 — pollution key inside a list element rejected."""
        body = 'name: x\ntools: [{"__proto__": "evil"}, "ok"]'
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_constructor_pollution_in_json_literal(self):
        """P1-09 — ``constructor`` key inside JSON-literal rejected."""
        body = 'name: x\ntools: {"constructor": "Function"}'
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_define_getter_inside_json_literal(self):
        body = 'name: x\ntools: {"k": {"__defineGetter__": "evil"}}'
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_clean_json_literal_passes(self):
        """Sanity: a clean JSON-literal is accepted unchanged."""
        body = 'name: x\ntools: {"read": true, "write": false}'
        p = _write(self.tmp, "agent.md", _fm(body))
        out = parse_agent_frontmatter(p)
        self.assertEqual(out["tools"], {"read": True, "write": False})

    def test_check_no_pollution_callable_raises(self):
        """Direct unit-test of the recursive walker."""
        with self.assertRaises(FrontmatterError):
            _check_no_pollution({"a": {"b": {"__proto__": 1}}})

    def test_check_no_pollution_depth_cap(self):
        """P1-09 — payloads deeper than LIMIT_DEPTH rejected."""
        # 12 nested dicts > LIMIT_DEPTH=8.
        deep: dict = {"k": "leaf"}
        for _ in range(15):
            deep = {"k": deep}
        with self.assertRaises(FrontmatterError):
            _check_no_pollution(deep)

    def test_check_no_pollution_array_cap(self):
        """P1-09 — list longer than LIMIT_ARRAY_LEN rejected."""
        from _lib.tier_policy._constants import LIMIT_ARRAY_LEN

        big_list = ["x"] * (LIMIT_ARRAY_LEN + 1)
        with self.assertRaises(FrontmatterError):
            _check_no_pollution(big_list)

    def test_check_no_pollution_clean_pass(self):
        """Clean nested payload passes silently."""
        clean = {"a": [1, 2, {"b": "ok"}], "c": True}
        # Should not raise.
        _check_no_pollution(clean)


class TestUnknownTopLevelKey(_FsBase):
    """R-CR Unseen #5 — closed-set allowlist for top-level keys."""

    def test_random_unknown_rejected(self):
        body = "name: x\nrandom_unknown_key: evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)

    def test_typo_in_known_key_rejected(self):
        body = "name: x\nrol: ceo"  # role mistyped
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)


class TestCanonicalPathReject(_FsBase):
    """R-CR1 / R-SEC4 / P0-03 — canonical agent paths refuse direct parsing."""

    def test_code_reviewer_canonical_rejected(self):
        """Hardcode floor role (on-disk; ALWAYS bind)."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "code-reviewer.md"
        target.write_text(_fm("name: cr"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_security_engineer_canonical_rejected(self):
        """Hardcode floor role (on-disk; ALWAYS bind)."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "security-engineer.md"
        target.write_text(_fm("name: sec"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_threat_detection_engineer_canonical_rejected(self):
        """Forward-looking floor role — guard active even pre-creation."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "threat-detection-engineer.md"
        target.write_text(_fm("name: td"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_identity_trust_architect_canonical_rejected(self):
        """Forward-looking floor role — guard active even pre-creation."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "identity-trust-architect.md"
        target.write_text(_fm("name: ita"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_incident_commander_canonical_rejected(self):
        """Forward-looking floor role — guard active even pre-creation."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "incident-commander.md"
        target.write_text(_fm("name: ic"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_llm_finops_architect_canonical_rejected(self):
        """Forward-looking floor role — guard active even pre-creation."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "llm-finops-architect.md"
        target.write_text(_fm("name: fin"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_ceo_canonical_rejected(self):
        """Legacy non-floor archetype — still canonically guarded."""
        canon_dir = self.tmp / ".claude" / "agents"
        canon_dir.mkdir(parents=True)
        target = canon_dir / "ceo.md"
        target.write_text(_fm("name: ceo"), encoding="utf-8")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(target)

    def test_canonical_list_size(self):
        """The local list mirrors the documented 10 agent slugs."""
        self.assertGreaterEqual(len(_LOCAL_CANONICAL_AGENT_PATHS), 10)

    def test_canonical_list_contains_six_spec_roles(self):
        """P0-03 — all 6 spec floor roles appear in the canonical list."""
        for role in (
            "code-reviewer",
            "security-engineer",
            "threat-detection-engineer",
            "identity-trust-architect",
            "incident-commander",
            "llm-finops-architect",
        ):
            self.assertTrue(
                any(p.endswith(f"/{role}.md") for p in _LOCAL_CANONICAL_AGENT_PATHS),
                msg=f"{role} not canonically guarded",
            )


class TestSizeCap(_FsBase):
    """R-SEC U2 — refuse files larger than 64 KiB before parse."""

    def test_oversize_rejected(self):
        # Build a body just over 64 KiB.
        body = "name: x\ndescription: " + ("a" * (66 * 1024))
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)


class TestDepthCap(_FsBase):
    """R-SEC U2 — refuse frontmatter blocks deeper than LIMIT_DEPTH."""

    def test_deeply_nested_rejected(self):
        # Nine levels of nested dicts — exceeds LIMIT_DEPTH=8.
        body = "name: x\ntools:\n"
        indent = "  "
        for i in range(9):
            body += indent * (i + 1) + f"k{i}:\n"
        body += indent * 10 + "leaf: y"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)


class TestNfkcNormalisation(_FsBase):
    """R-SEC6 — NFKC-fold scalars before downstream regex."""

    def test_fullwidth_a_folded(self):
        # U+FF41 fullwidth latin small letter a → "a"
        body = "name: ａbc"
        p = _write(self.tmp, "agent.md", _fm(body))
        out = parse_agent_frontmatter(p)
        self.assertEqual(
            out["name"], unicodedata.normalize("NFKC", "ａbc")
        )
        self.assertEqual(out["name"], "abc")


class TestSymlinkReject(_FsBase):
    """Reject leaf symlinks."""

    def test_symlink_rejected(self):
        if os.name != "posix":  # pragma: no cover
            self.skipTest("symlink test posix-only")
        real = _write(self.tmp, "real.md", _fm("name: x"))
        link = self.tmp / "agent.md"
        link.symlink_to(real)
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(link)


class TestTabsRejected(_FsBase):
    """Tabs are explicitly disallowed in indentation."""

    def test_tab_indent_rejected(self):
        body = "name: x\ntools:\n\t- evil"
        p = _write(self.tmp, "agent.md", _fm(body))
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)


class TestUnterminatedFrontmatter(_FsBase):
    """A leading ``---`` without closing delimiter is a parse error."""

    def test_unterminated_frontmatter(self):
        p = _write(self.tmp, "agent.md", "---\nname: x\nno-end\n")
        with self.assertRaises(FrontmatterError):
            parse_agent_frontmatter(p)


class TestByteIdentityStability(_FsBase):
    """Same input → same parsed dict (deterministic)."""

    def test_repeat_parse_identical(self):
        body = "name: alice\nrole: ceo\nmodel: claude-opus-4-8"
        p = _write(self.tmp, "agent.md", _fm(body))
        a = parse_agent_frontmatter(p)
        b = parse_agent_frontmatter(p)
        self.assertEqual(a, b)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
