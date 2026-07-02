"""test_types.py — coverage for tier_policy._types.

Targets the staged module at
``.claude/plans/PLAN-071/staging/tier_policy/_types.py``.

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1            — symbol path is ``tier_policy._types.ROLE_TO_TASK_TYPES``
                     (no shadow under ``_lib/policy.py``).
* R-CR R2-2        — MODEL_ID enum: 3 canonical slugs; legacy
                     ``claude-opus-4-1`` is rejected.
* R-CR Unseen #2   — frozen dataclasses + MappingProxyType make mutation raise.
* R-CR Unseen #5   — prototype-pollution keys absent from ROLE_TO_TASK_TYPES.
* R-SEC4 / P0-03   — ROLE_TO_TASK_TYPES.keys() is a strict superset of
                     EXPECTED_VETO_FLOOR_UNION (6 spec roles per
                     PLAN-071 §3.1 line 151).

Forward-looking note (P0-03)
----------------------------

4 of the 6 spec floor roles (``threat-detection-engineer``,
``identity-trust-architect``, ``incident-commander``,
``llm-finops-architect``) do NOT yet have ``.claude/agents/<role>.md``
files on disk. Tests below assert ROLE_TO_TASK_TYPES recognises their
task-type ownership independent of on-disk presence.

Stdlib-only. Python ≥ 3.9.
"""

from __future__ import annotations

import dataclasses
import unittest
from types import MappingProxyType

from _lib.tier_policy import _constants as C
from _lib.tier_policy import _types as T


class TestModelIdEnum(unittest.TestCase):
    """R-CR R2-2 — closed-membership enum of canonical model slugs."""

    def test_enum_has_four_members(self):
        # 3 → 4: SONNET5 added by ADR-157 (PLAN-152 sonnet5-tier).
        members = list(T.MODEL_ID)
        self.assertEqual(len(members), 4)

    def test_opus47_value(self):
        self.assertEqual(T.MODEL_ID.OPUS47.value, "claude-opus-4-8")

    def test_sonnet46_value(self):
        self.assertEqual(T.MODEL_ID.SONNET46.value, "claude-sonnet-4-6")

    def test_sonnet5_value(self):
        # ADR-157: exact wire string, no date suffix.
        self.assertEqual(T.MODEL_ID.SONNET5.value, "claude-sonnet-5")

    def test_haiku45_value(self):
        self.assertEqual(T.MODEL_ID.HAIKU45.value, "claude-haiku-4-5")

    def test_legacy_opus_4_1_rejected(self):
        """R-CR R2-2 — legacy slug ``claude-opus-4-1`` is NOT a member."""
        with self.assertRaises(ValueError):
            T.MODEL_ID("claude-opus-4-1")

    def test_unknown_slug_rejected(self):
        with self.assertRaises(ValueError):
            T.MODEL_ID("gpt-4o")

    def test_lookup_by_value_round_trips(self):
        for member in T.MODEL_ID:
            self.assertIs(T.MODEL_ID(member.value), member)

    def test_str_returns_value(self):
        self.assertEqual(str(T.MODEL_ID.OPUS47), "claude-opus-4-8")


class TestTaskTypeRequest(unittest.TestCase):
    """R-CR Unseen #2 — frozen dataclass."""

    def test_is_dataclass(self):
        self.assertTrue(dataclasses.is_dataclass(T.TaskTypeRequest))

    def test_is_frozen(self):
        params = T.TaskTypeRequest.__dataclass_params__  # type: ignore[attr-defined]
        self.assertTrue(params.frozen)

    def test_construct_minimal(self):
        req = T.TaskTypeRequest(task_type="diff-review", role="code-reviewer")
        self.assertEqual(req.task_type, "diff-review")
        self.assertEqual(req.role, "code-reviewer")
        self.assertEqual(req.context_tokens, 0)
        self.assertEqual(req.risk_level, "medium")

    def test_mutation_raises_frozen_instance_error(self):
        req = T.TaskTypeRequest(task_type="x", role="ceo")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            req.task_type = "evil"  # type: ignore[misc]

    def test_field_set_complete(self):
        names = {f.name for f in dataclasses.fields(T.TaskTypeRequest)}
        self.assertEqual(
            names, {"task_type", "role", "context_tokens", "risk_level"}
        )


class TestTaskTypeResponse(unittest.TestCase):
    """R-CR Unseen #2 — frozen dataclass; advisory-only contract."""

    def test_is_dataclass(self):
        self.assertTrue(dataclasses.is_dataclass(T.TaskTypeResponse))

    def test_is_frozen(self):
        params = T.TaskTypeResponse.__dataclass_params__  # type: ignore[attr-defined]
        self.assertTrue(params.frozen)

    def test_default_confidence_zero(self):
        resp = T.TaskTypeResponse(
            mode="M", suggested_model="claude-opus-4-8", reason="x"
        )
        self.assertEqual(resp.confidence, 0.0)

    def test_mutation_raises_frozen_instance_error(self):
        resp = T.TaskTypeResponse(
            mode="M", suggested_model="claude-opus-4-8", reason="x"
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            resp.mode = "XL"  # type: ignore[misc]

    def test_field_set_complete(self):
        names = {f.name for f in dataclasses.fields(T.TaskTypeResponse)}
        self.assertEqual(
            names, {"mode", "suggested_model", "reason", "confidence"}
        )


class TestClassificationResultAlias(unittest.TestCase):
    """R-CR1 — ClassificationResult is exactly the TaskTypeResponse alias."""

    def test_alias_is_response(self):
        self.assertIs(T.ClassificationResult, T.TaskTypeResponse)


class TestRoleToTaskTypes(unittest.TestCase):
    """R-CR1 + R-SEC4 / P0-03 + R-CR Unseen #5."""

    def test_is_mapping_proxy_type(self):
        """R-CR Unseen #2 — runtime mutation must raise."""
        self.assertIsInstance(T.ROLE_TO_TASK_TYPES, MappingProxyType)

    def test_mutation_raises_type_error(self):
        with self.assertRaises(TypeError):
            T.ROLE_TO_TASK_TYPES["evil-role"] = frozenset({"x"})  # type: ignore[index]

    def test_superset_of_expected_veto_floor_union(self):
        """P0-03 / R-SEC4 — strict superset of the 6 spec floor roles.

        This is THE structural test asserted by ``task-route.py`` at
        script init: ``classifier_floor >= EXPECTED_VETO_FLOOR_UNION``.
        """
        union_keys = set(C.EXPECTED_VETO_FLOOR_UNION)
        role_keys = set(T.ROLE_TO_TASK_TYPES.keys())
        self.assertTrue(
            union_keys.issubset(role_keys),
            msg=f"missing spec floor roles: {union_keys - role_keys}",
        )

    def test_superset_of_veto_hardcode_keys(self):
        """The 2 hardcode floor roles are also in ROLE_TO_TASK_TYPES."""
        veto_keys = set(C.VETO_HARDCODE.keys())
        role_keys = set(T.ROLE_TO_TASK_TYPES.keys())
        self.assertTrue(
            veto_keys.issubset(role_keys),
            msg=f"missing hardcode floor roles: {veto_keys - role_keys}",
        )

    def test_includes_all_six_spec_floor_roles(self):
        """P0-03 — ALL 6 spec roles per PLAN-071 §3.1 line 151."""
        for role in (
            "code-reviewer",
            "security-engineer",
            "threat-detection-engineer",
            "identity-trust-architect",
            "incident-commander",
            "llm-finops-architect",
        ):
            self.assertIn(role, T.ROLE_TO_TASK_TYPES)

    def test_includes_legacy_team_archetypes(self):
        """The legacy team archetypes (qa/perf/devops/ceo) still
        present for routing — they just don't VETO."""
        for role in ("qa-architect", "performance-engineer", "devops", "ceo"):
            self.assertIn(role, T.ROLE_TO_TASK_TYPES)

    def test_no_prototype_pollution_keys(self):
        """R-CR Unseen #5 — table free of ``__proto__`` / ``constructor`` / ``prototype``."""
        for forbidden in ("__proto__", "constructor", "prototype"):
            self.assertNotIn(forbidden, T.ROLE_TO_TASK_TYPES)

    def test_values_are_frozensets(self):
        for role, task_types in T.ROLE_TO_TASK_TYPES.items():
            self.assertIsInstance(
                task_types, frozenset, msg=f"role={role}"
            )

    def test_values_nonempty(self):
        for role, task_types in T.ROLE_TO_TASK_TYPES.items():
            self.assertGreater(
                len(task_types), 0, msg=f"role={role} empty"
            )

    def test_forward_looking_roles_have_distinct_task_types(self):
        """P0-03 — the 4 forward-looking roles MUST own task-types
        beyond the generic veto-arbitration sentinel.

        Even though their agent files are not yet on disk, the
        classifier needs to know their domain ownership.
        """
        for role in (
            "threat-detection-engineer",
            "identity-trust-architect",
            "incident-commander",
            "llm-finops-architect",
        ):
            task_types = T.ROLE_TO_TASK_TYPES[role]
            # Each forward-looking role owns ≥ 4 distinct task-types
            # PLUS veto-arbitration (5 minimum).
            self.assertGreaterEqual(
                len(task_types),
                5,
                msg=f"forward-looking role {role} owns too few task-types",
            )


class TestSchemaVersion(unittest.TestCase):
    def test_is_two(self):
        self.assertEqual(T.SCHEMA_VERSION, 2)

    def test_matches_constants(self):
        self.assertEqual(T.SCHEMA_VERSION, C.CURRENT_SCHEMA_VERSION)


class TestHelpers(unittest.TestCase):
    def test_task_types_for_known_role(self):
        self.assertGreater(len(T.task_types_for_role("code-reviewer")), 0)

    def test_task_types_for_unknown_role(self):
        self.assertEqual(T.task_types_for_role("nonexistent"), frozenset())

    def test_task_types_for_forward_looking_role(self):
        """P0-03 — forward-looking spec roles return non-empty task-types."""
        for role in (
            "threat-detection-engineer",
            "identity-trust-architect",
            "incident-commander",
            "llm-finops-architect",
        ):
            self.assertGreater(
                len(T.task_types_for_role(role)),
                0,
                msg=f"forward-looking role={role} returned empty",
            )

    def test_is_known_mode(self):
        self.assertTrue(T.is_known_mode("M"))
        self.assertFalse(T.is_known_mode("XS"))

    def test_is_known_model(self):
        self.assertTrue(T.is_known_model("claude-opus-4-8"))
        self.assertFalse(T.is_known_model("claude-opus-4-1"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
