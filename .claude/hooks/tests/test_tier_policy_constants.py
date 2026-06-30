"""test_constants.py — coverage for tier_policy._constants.

Targets the staged module at
``.claude/plans/PLAN-071/staging/tier_policy/_constants.py``.

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1   — symbol path is ``tier_policy._constants.VETO_HARDCODE`` (not
            ``_lib/policy.py``).
* R-CR2   — ``FROZEN_BASELINE_SHA256`` is stable, hex, recomputable, AND
            equals the hardcoded ``_EXPECTED_FROZEN_BASELINE_SHA256``.
* R-SEC4 / P0-03 — VETO_HARDCODE keys = exactly **2 hardcode floor roles**
            (code-reviewer + security-engineer); the **5-role spec union**
            (PLAN-074 Wave 1c reduced 6→5; ``llm-finops-architect``
            excluded per matrix) lives in ``EXPECTED_VETO_FLOOR_UNION``.
* R-CR Unseen #2 — ``MappingProxyType`` makes mutation raise.
* P1-10   — drift detector via hardcoded expected digest assertion.

Wave 1c roles note (PLAN-074, S93)
-----------------------------------

The 3 Wave 1c security-domain VETO-floor roles (``threat-detection-engineer``,
``identity-trust-architect``, ``incident-commander``) appear in
``EXPECTED_VETO_FLOOR_UNION``. After Wave 1c shipped, every union role
has a deployed ``.claude/agents/<role>.md`` file — atomic-add invariant
per S90 P0-01 lesson, enforced bidirectionally by
``test_veto_floor_bijection.py``. ``llm-finops-architect`` is EXCLUDED
from the union per Wave 1c matrix (cost ≠ security; ADR-052 amendment).
Tests below assert the spec contract AND the deployment correspondence.

Stdlib-only. Python ≥ 3.9. ``from __future__ import annotations``.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest

from _lib import tier_policy
from _lib.tier_policy import _constants as C


class TestVetoHardcode(unittest.TestCase):
    """R-SEC4 / P0-03 + R-CR1 coverage of the **2-role hardcode floor**.

    The 2 roles below are the ones with on-disk agent definition files
    AND the ones enforceable from this module without crossing the
    ``_lib/`` boundary. The 4 remaining spec floor roles live in
    ``EXPECTED_VETO_FLOOR_UNION`` — see ``TestExpectedVetoFloorUnion``.
    """

    EXPECTED_HARDCODE_ROLES = frozenset({
        "code-reviewer",
        "security-engineer",
    })

    def test_keys_exactly_two(self):
        """P0-03 — exactly 2 hardcode roles per PLAN-071 §4.2 line 380."""
        self.assertEqual(len(C.VETO_HARDCODE), 2)

    def test_keys_match_hardcode_subset(self):
        """P0-03 — keys == 2 hardcode roles (code-reviewer + sec-eng)."""
        self.assertEqual(
            set(C.VETO_HARDCODE.keys()), self.EXPECTED_HARDCODE_ROLES
        )

    def test_hardcode_subset_of_expected_union(self):
        """P0-03 — VETO_HARDCODE.keys() ⊆ EXPECTED_VETO_FLOOR_UNION."""
        self.assertTrue(
            set(C.VETO_HARDCODE.keys()).issubset(C.EXPECTED_VETO_FLOOR_UNION)
        )

    def test_each_role_has_nonempty_task_types(self):
        """Every role owns ≥ 1 task-type slug."""
        for role, task_types in C.VETO_HARDCODE.items():
            self.assertTrue(
                len(task_types) >= 1,
                msg=f"role {role} has empty task-types frozenset",
            )

    def test_task_types_are_frozensets(self):
        """Values are ``frozenset`` (mutation should raise)."""
        for role, task_types in C.VETO_HARDCODE.items():
            self.assertIsInstance(
                task_types, frozenset, msg=f"{role} value not frozenset"
            )

    def test_symbol_path_is_tier_policy_constants(self):
        """R-CR1 — symbol resolves under ``tier_policy._constants``."""
        # Module-level access; ImportError would fail the whole file.
        self.assertIs(tier_policy.VETO_HARDCODE, C.VETO_HARDCODE)

    def test_no_legacy_lib_policy_import(self):
        """R-CR1 — _constants.py source must not import _lib.policy."""
        import inspect

        src = inspect.getsource(C)
        # Allow a comment mentioning _lib.policy; reject an actual import.
        self.assertNotIn("from _lib.policy", src)
        self.assertNotIn("import _lib.policy", src)
        self.assertNotIn("from _lib import policy", src)


class TestExpectedVetoFloorUnion(unittest.TestCase):
    """P0-03 — the 5-role spec contract (PLAN-074 Wave 1c reduced 6→5).

    PLAN-071 §3.1 line 151 originally specified a 6-role union; PLAN-074
    Wave 1c amendment (S93) excluded ``llm-finops-architect`` per the
    Wave 1c VETO-floor matrix and ADR-052 amendment — cost governance
    is operational doctrine + mechanical enforcement (ADR-064), NOT a
    sub-domain trust boundary that justifies a dedicated VETO authority.
    """

    EXPECTED_SPEC_ROLES = frozenset({
        "code-reviewer",
        "security-engineer",
        "threat-detection-engineer",
        "identity-trust-architect",
        "incident-commander",
    })

    # Wave 1c security-domain VETO-floor roles. After S93, every role in
    # the union has a deployed ``.claude/agents/<role>.md`` file —
    # atomic-add invariant per S90 P0-01 lesson, enforced bidirectionally
    # by ``test_veto_floor_bijection.py``.
    SECURITY_DOMAIN_VETO_ROLES = frozenset({
        "threat-detection-engineer",
        "identity-trust-architect",
        "incident-commander",
    })

    def test_size_is_five(self):
        """PLAN-074 Wave 1c — exactly 5 roles per matrix amendment."""
        self.assertEqual(len(C.EXPECTED_VETO_FLOOR_UNION), 5)

    def test_membership_matches_spec(self):
        """PLAN-074 Wave 1c — exact 5-role set per matrix verbatim."""
        self.assertEqual(
            set(C.EXPECTED_VETO_FLOOR_UNION), self.EXPECTED_SPEC_ROLES
        )

    def test_llm_finops_architect_excluded(self):
        """PLAN-074 Wave 1c matrix — cost ≠ security; explicit exclusion.

        ADR-052 amendment + Wave 1c VETO-floor matrix exclude
        ``llm-finops-architect`` from the union; the agent file ships
        with ``veto_floor: false`` so the exclusion is bidirectionally
        verifiable (see test_veto_floor_bijection.py).
        """
        self.assertNotIn(
            "llm-finops-architect", C.EXPECTED_VETO_FLOOR_UNION
        )

    def test_is_frozenset(self):
        """Defence-in-depth: mutation must raise."""
        self.assertIsInstance(C.EXPECTED_VETO_FLOOR_UNION, frozenset)

    def test_contains_two_hardcode_roles(self):
        """The 2 hardcode roles MUST appear in the union."""
        for role in ("code-reviewer", "security-engineer"):
            self.assertIn(role, C.EXPECTED_VETO_FLOOR_UNION)

    def test_contains_three_security_domain_roles(self):
        """The 3 Wave 1c security-domain VETO-floor roles MUST appear in the union.

        After PLAN-074 Wave 1c (S93), every role in this set has a
        deployed ``.claude/agents/<role>.md`` file. ``llm-finops-architect``
        is NOT in this set (excluded per Wave 1c matrix; ships as
        advisory archetype with ``veto_floor: false``).
        """
        for role in self.SECURITY_DOMAIN_VETO_ROLES:
            self.assertIn(role, C.EXPECTED_VETO_FLOOR_UNION)

    def test_no_legacy_team_archetypes(self):
        """The legacy 4 (qa-architect/perf-eng/devops/ceo) are NOT in
        the spec floor — they are routed but not VETO-binding."""
        for role in ("qa-architect", "performance-engineer", "devops", "ceo"):
            self.assertNotIn(role, C.EXPECTED_VETO_FLOOR_UNION)


class TestVetoHardcodeImmutability(unittest.TestCase):
    """R-CR Unseen #2 — runtime mutation must raise."""

    def test_assigning_new_key_raises(self):
        with self.assertRaises(TypeError):
            C.VETO_HARDCODE["evil-role"] = frozenset({"x"})  # type: ignore[index]

    def test_assigning_existing_key_raises(self):
        with self.assertRaises(TypeError):
            C.VETO_HARDCODE["code-reviewer"] = frozenset({"x"})  # type: ignore[index]

    def test_deleting_key_raises(self):
        with self.assertRaises(TypeError):
            del C.VETO_HARDCODE["code-reviewer"]  # type: ignore[attr-defined]

    def test_frozenset_value_cannot_be_mutated(self):
        """Each ``frozenset`` value rejects ``add`` / ``discard``."""
        for role, task_types in C.VETO_HARDCODE.items():
            with self.assertRaises(AttributeError, msg=f"role={role}"):
                task_types.add("smuggled")  # type: ignore[attr-defined]


class TestFrozenBaselineSha256(unittest.TestCase):
    """R-CR2 + P1-10 — drift / tamper detector for the floor mapping."""

    HEX_RE = re.compile(r"^[0-9a-f]{64}$")

    def test_is_64_char_hex(self):
        self.assertIsInstance(C.FROZEN_BASELINE_SHA256, str)
        self.assertTrue(self.HEX_RE.match(C.FROZEN_BASELINE_SHA256))

    def test_is_lowercase(self):
        self.assertEqual(
            C.FROZEN_BASELINE_SHA256, C.FROZEN_BASELINE_SHA256.lower()
        )

    def test_recomputation_matches(self):
        """Recompute the digest with the documented algorithm and compare.

        P1-10 fix: digest now covers BOTH ``VETO_HARDCODE`` AND
        ``EXPECTED_VETO_FLOOR_UNION``. Drift in either source trips.
        """
        payload = {
            "veto_hardcode": {
                role: sorted(task_types)
                for role, task_types in sorted(C.VETO_HARDCODE.items())
            },
            "expected_veto_floor_union": sorted(
                C.EXPECTED_VETO_FLOOR_UNION
            ),
        }
        blob = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        recomputed = hashlib.sha256(blob).hexdigest()
        self.assertEqual(recomputed, C.FROZEN_BASELINE_SHA256)

    def test_hardcoded_expected_matches_computed(self):
        """P1-10 — _EXPECTED_FROZEN_BASELINE_SHA256 == FROZEN_BASELINE_SHA256.

        If this fails, the module-load assertion would have already
        thrown at import time; this test is belt-and-braces.
        """
        self.assertEqual(
            C._EXPECTED_FROZEN_BASELINE_SHA256, C.FROZEN_BASELINE_SHA256
        )

    def test_is_module_level_constant(self):
        """Two attribute reads return the same string identity."""
        a = C.FROZEN_BASELINE_SHA256
        b = C.FROZEN_BASELINE_SHA256
        self.assertEqual(a, b)


class TestClassificationModes(unittest.TestCase):
    """Closed enum of S/M/L/XL slugs."""

    def test_exact_tuple(self):
        self.assertEqual(C.CLASSIFICATION_MODES, ("S", "M", "L", "XL"))

    def test_is_tuple_not_list(self):
        """Tuple => positional immutability."""
        self.assertIsInstance(C.CLASSIFICATION_MODES, tuple)

    def test_order_is_load_bearing(self):
        """``index()`` is used as a numeric tier — order matters."""
        self.assertEqual(C.CLASSIFICATION_MODES.index("S"), 0)
        self.assertEqual(C.CLASSIFICATION_MODES.index("XL"), 3)

    def test_no_unexpected_modes(self):
        """No legacy slug like ``"XS"`` snuck in."""
        for unwanted in ("XS", "XXL", "MEDIUM", "small", ""):
            self.assertNotIn(unwanted, C.CLASSIFICATION_MODES)


class TestHardLimits(unittest.TestCase):
    """Defence-in-depth size / depth constants mirror SPEC §3.3."""

    def test_limit_file_bytes(self):
        self.assertEqual(C.LIMIT_FILE_BYTES, 64 * 1024)

    def test_limit_depth(self):
        self.assertEqual(C.LIMIT_DEPTH, 8)

    def test_limit_key_count(self):
        self.assertGreaterEqual(C.LIMIT_KEY_COUNT, 100)

    def test_limit_scalar_len(self):
        self.assertGreaterEqual(C.LIMIT_SCALAR_LEN, 1024)

    def test_limit_array_len_present(self):
        """P1-09 — array-length cap exposed for nested-payload guard."""
        self.assertTrue(hasattr(C, "LIMIT_ARRAY_LEN"))
        self.assertGreaterEqual(C.LIMIT_ARRAY_LEN, 1000)

    def test_current_schema_version_is_2(self):
        self.assertEqual(C.CURRENT_SCHEMA_VERSION, 2)


class TestAllowedFrontmatterKeys(unittest.TestCase):
    """Closed-set allowlist for agent frontmatter top-level keys."""

    def test_is_frozenset(self):
        self.assertIsInstance(C._ALLOWED_FRONTMATTER_KEYS, frozenset)

    def test_required_keys_present(self):
        for key in ("name", "description", "model", "role"):
            self.assertIn(key, C._ALLOWED_FRONTMATTER_KEYS)


class TestFrozenBaselineFallbackShape(unittest.TestCase):
    """``FROZEN_BASELINE.veto_floor_roles`` projects the 5-role union (Wave 1c)."""

    def test_veto_floor_roles_field_five_roles(self):
        """PLAN-074 Wave 1c — fallback advertises 5-role spec contract, not 2 nor 6."""
        roles = C.FROZEN_BASELINE["veto_floor_roles"]
        self.assertEqual(len(roles), 5)

    def test_veto_floor_roles_sorted(self):
        """Determinism: the field is lex-sorted for stable serialisation."""
        roles = C.FROZEN_BASELINE["veto_floor_roles"]
        self.assertEqual(roles, sorted(roles))

    def test_veto_floor_roles_matches_expected_union(self):
        roles = C.FROZEN_BASELINE["veto_floor_roles"]
        self.assertEqual(set(roles), set(C.EXPECTED_VETO_FLOOR_UNION))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
