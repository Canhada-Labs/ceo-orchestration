"""Tests for parallelization-by-default skill (PLAN-083 Wave 0a sub-0.1).

Validates that the staged SKILL.md:
1. Exists at the expected staging path (future canonical mirror).
2. Has frontmatter that conforms to the required-field subset of
   `.claude/policies/schemas/repo-profile-skill-binding.schema.json`.
3. Has the required body sections per the sub-agent spec.
4. Encodes the <=6 parallelization ceiling (Perf P0-1 in PLAN-083).
5. Uses the correct audit-action naming convention (snake_case, no `_emit`).

Stdlib-only. No external deps. Python >= 3.9. Tolerant of running from
either the staging dir OR the canonical post-apply path.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path resolution — dual-mode (staging OR canonical).
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[7]
STAGING_SKILL = (
    REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-083"
    / "staging"
    / "wave-0a"
    / "sub-0-1-parallelization"
    / "SKILL.md"
)
CANONICAL_SKILL = (
    REPO_ROOT
    / ".claude"
    / "skills"
    / "core"
    / "parallelization-by-default"
    / "SKILL.md"
)
SCHEMA_PATH = (
    REPO_ROOT
    / ".claude"
    / "policies"
    / "schemas"
    / "repo-profile-skill-binding.schema.json"
)


def _resolve_skill_path() -> Path:
    """Prefer canonical (if applied) else staging. Both are accepted."""
    if CANONICAL_SKILL.is_file():
        return CANONICAL_SKILL
    return STAGING_SKILL


# ---------------------------------------------------------------------------
# Frontmatter parser — stdlib YAML-subset (we know the shape we wrote).
# ---------------------------------------------------------------------------

def _read_frontmatter(skill_path: Path) -> Tuple[Dict[str, Any], str]:
    """Return (frontmatter_dict, body_text). Hand-rolled to avoid PyYAML dep.

    Supports: top-level scalar `key: value`, nested mapping under a key
    with indented `key: value` children, lists with `- key: value` items,
    bool/int auto-cast, quoted strings stripped.
    """
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_path} missing leading '---' frontmatter")
    closer = text.find("\n---\n", 4)
    if closer < 0:
        raise ValueError(f"{skill_path} missing trailing '---' frontmatter")
    front_block = text[4:closer]
    body = text[closer + 5 :]
    return _parse_yaml_subset(front_block), body


def _cast_scalar(value: str) -> Any:
    value = value.strip()
    if value == "" or value is None:
        return value
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _parse_yaml_subset(text: str) -> Dict[str, Any]:
    """Tiny YAML parser sufficient for our frontmatter shape."""
    lines = text.split("\n")
    root: Dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw.startswith(" "):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue
        key, _, rest = raw.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Block — could be a mapping or a list.
            block_lines: List[str] = []
            j = i + 1
            while j < len(lines) and (
                lines[j].startswith(" ") or lines[j].startswith("\t") or lines[j].strip() == ""
            ):
                block_lines.append(lines[j])
                j += 1
            root[key] = _parse_block(block_lines)
            i = j
        else:
            # Inline scalar — but watch for description folded across lines.
            # Treat continuation as multi-line if next line starts with 2+ spaces
            # AND does not contain a colon at the leading indented level.
            scalar_lines = [rest]
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == "":
                    break
                if not (nxt.startswith("  ") or nxt.startswith("\t")):
                    break
                # Continuation only if the line doesn't itself look like a key
                stripped = nxt.strip()
                if ": " in stripped and not stripped.startswith("- "):
                    # Could still be a continuation of folded string, but
                    # for safety treat as new key at same level => stop.
                    break
                scalar_lines.append(stripped)
                j += 1
            joined = " ".join(scalar_lines)
            root[key] = _cast_scalar(joined)
            i = j
    return root


def _parse_block(block_lines: List[str]) -> Any:
    """Parse an indented block — list (lines start with '-') or mapping."""
    cleaned = [ln for ln in block_lines if ln.strip()]
    if not cleaned:
        return {}
    first_strip = cleaned[0].lstrip()
    if first_strip.startswith("- "):
        return _parse_block_list(cleaned)
    return _parse_block_mapping(cleaned)


def _common_indent(lines: List[str]) -> int:
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in lines if ln.strip()]
    return min(indents) if indents else 0


def _parse_block_mapping(lines: List[str]) -> Dict[str, Any]:
    base = _common_indent(lines)
    dedented = [ln[base:] if ln.startswith(" " * base) else ln for ln in lines]
    return _parse_yaml_subset("\n".join(dedented))


def _parse_block_list(lines: List[str]) -> List[Any]:
    base = _common_indent(lines)
    items: List[Any] = []
    cur: List[str] = []
    for ln in lines:
        body = ln[base:] if ln.startswith(" " * base) else ln
        if body.startswith("- "):
            if cur:
                items.append(_parse_list_item(cur))
                cur = []
            cur.append(body[2:])
        else:
            cur.append(body[2:] if body.startswith("  ") else body)
    if cur:
        items.append(_parse_list_item(cur))
    return items


def _parse_list_item(lines: List[str]) -> Any:
    """A list item may be a scalar 'event: spawn-requested' or a sub-mapping."""
    if len(lines) == 1 and ":" in lines[0]:
        k, _, v = lines[0].partition(":")
        return {k.strip(): _cast_scalar(v.strip())}
    return _parse_yaml_subset("\n".join(lines))


# ---------------------------------------------------------------------------
# Hand-rolled schema validator (required fields + enums + types).
# ---------------------------------------------------------------------------

def _validate_schema(fm: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Return a list of validation error messages (empty == valid)."""
    errors: List[str] = []
    required = schema.get("required", [])
    for r in required:
        if r not in fm:
            errors.append(f"missing required field: {r}")

    if "priority" in fm:
        p = fm["priority"]
        if not isinstance(p, int) or p < 1 or p > 10:
            errors.append(f"priority must be int in [1,10], got {p!r}")

    if "risk_class" in fm:
        if fm["risk_class"] not in ("low", "medium", "high"):
            errors.append(f"risk_class must be one of low/medium/high, got {fm['risk_class']!r}")

    if "domain" in fm:
        if not isinstance(fm["domain"], str) or len(fm["domain"]) < 2:
            errors.append(f"domain must be string len>=2, got {fm['domain']!r}")

    if "context_budget_tokens" in fm:
        ctb = fm["context_budget_tokens"]
        if not isinstance(ctb, int) or ctb < 0 or ctb > 30000:
            errors.append(f"context_budget_tokens must be int in [0,30000], got {ctb!r}")

    if "inactive_but_retained" in fm:
        if not isinstance(fm["inactive_but_retained"], bool):
            errors.append("inactive_but_retained must be bool")

    if "repo_profile_binding" in fm:
        rpb = fm["repo_profile_binding"]
        if not isinstance(rpb, dict):
            errors.append("repo_profile_binding must be a mapping")
        else:
            allowed_profiles = {"frontend", "engine", "fintech", "trading-readonly", "generic"}
            for prof, entry in rpb.items():
                if prof not in allowed_profiles:
                    errors.append(f"unknown profile {prof!r}")
                    continue
                if not isinstance(entry, dict):
                    errors.append(f"profile {prof!r} entry must be mapping")
                    continue
                if "active" not in entry:
                    errors.append(f"profile {prof!r} missing 'active'")
                if "priority" not in entry:
                    errors.append(f"profile {prof!r} missing 'priority'")
                else:
                    pp = entry["priority"]
                    if not isinstance(pp, int) or pp < 1 or pp > 10:
                        errors.append(f"profile {prof!r} priority not in [1,10]: {pp!r}")
    return errors


# ---------------------------------------------------------------------------
# Lightweight CEO-transcript ceiling detector (used by ceiling-enforcement
# unit test). Parses prose like "dispatch 7 sub-agents in parallel".
# ---------------------------------------------------------------------------

_DISPATCH_RE = re.compile(
    r"dispatch(?:ing)?\s+(\d+)\s+sub[- ]agents?\s+in\s+parallel",
    re.IGNORECASE,
)


def detect_ceiling_violation(transcript: str, ceiling: int = 6) -> Optional[str]:
    """Return a warning string if transcript proposes >ceiling parallel dispatch."""
    m = _DISPATCH_RE.search(transcript)
    if not m:
        return None
    n = int(m.group(1))
    if n > ceiling:
        return (
            f"ceiling violation: transcript proposes {n} parallel sub-agents; "
            f"hard cap is {ceiling} (PLAN-083 Perf P0-1)"
        )
    return None


# ---------------------------------------------------------------------------
# Toy decomposition recommender (mirrors the algorithm in the SKILL body).
# ---------------------------------------------------------------------------

def recommend_dispatch(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Given items each {id, deps:[], shared_files:[]}, return a decision.

    Returns dict with 'mode' ('parallel'|'serial'|'batched') and 'reason'.
    """
    n = len(items)
    if n < 3:
        return {"mode": "serial", "reason": "serial_single_item", "n": n}
    # Cycle / chain detection: if every item has >=1 dep on another item,
    # treat as a chain (serial).
    has_any_dep = any(it.get("deps") for it in items)
    leaves = [it for it in items if not it.get("deps")]
    if has_any_dep and len(leaves) < 3:
        return {"mode": "serial", "reason": "serial_dependency_chain", "n": n}

    # Shared-file write contention.
    seen_files: Dict[str, str] = {}
    for it in items:
        for f in it.get("shared_files", []):
            if f in seen_files and seen_files[f] != it["id"]:
                return {
                    "mode": "serial",
                    "reason": "serial_shared_file_write",
                    "n": n,
                }
            seen_files[f] = it["id"]

    if n > 6:
        return {"mode": "batched", "reason": "batched_overflow", "n": n, "batch_size": 6}
    return {"mode": "parallel", "reason": "parallel_chosen", "n": n}


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestSkillExistsAndParses(unittest.TestCase):
    def test_skill_md_exists(self) -> None:
        path = _resolve_skill_path()
        self.assertTrue(
            path.is_file(),
            f"SKILL.md not found at {path} (staging={STAGING_SKILL}, canonical={CANONICAL_SKILL})",
        )

    def test_skill_md_has_frontmatter(self) -> None:
        path = _resolve_skill_path()
        fm, body = _read_frontmatter(path)
        self.assertIsInstance(fm, dict)
        self.assertGreater(len(body.strip()), 100, "body suspiciously empty")


class TestFrontmatterSchemaCompliance(unittest.TestCase):
    def setUp(self) -> None:
        self.fm, _ = _read_frontmatter(_resolve_skill_path())
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_required_fields_present(self) -> None:
        errors = _validate_schema(self.fm, self.schema)
        self.assertEqual(errors, [], f"schema errors: {errors}")

    def test_all_five_profiles_bound(self) -> None:
        rpb = self.fm.get("repo_profile_binding", {})
        for prof in ("frontend", "engine", "fintech", "trading-readonly", "generic"):
            self.assertIn(prof, rpb, f"missing profile binding: {prof}")
            self.assertTrue(rpb[prof].get("active"), f"{prof} should be active=true")

    def test_priority_high_precedence(self) -> None:
        # Foundational primitive => priority 2 per task brief.
        self.assertEqual(self.fm.get("priority"), 2)
        self.assertEqual(self.fm.get("risk_class"), "low")
        self.assertFalse(self.fm.get("inactive_but_retained", True))


class TestBodyRequiredSections(unittest.TestCase):
    def setUp(self) -> None:
        _, self.body = _read_frontmatter(_resolve_skill_path())

    def test_body_has_when_to_invoke_section(self) -> None:
        self.assertRegex(self.body, r"(?im)^##\s+When to invoke\b")

    def test_body_has_decomposition_algorithm_section(self) -> None:
        self.assertRegex(self.body, r"(?im)^##\s+Decomposition algorithm")

    def test_body_has_ceiling_section(self) -> None:
        self.assertRegex(self.body, r"(?im)^##\s+Ceiling enforcement")
        # ceiling number must literally appear.
        self.assertIn("6", self.body)
        self.assertRegex(
            self.body,
            r"(?i)(<=\s*6|<= 6|cap.*6|max(imum)?\s+6|6\s+parallel)",
        )

    def test_body_has_anti_patterns_section(self) -> None:
        self.assertRegex(self.body, r"(?im)^##\s+Anti-patterns")


class TestCeilingEnforcement(unittest.TestCase):
    def test_seven_parallel_triggers_warning(self) -> None:
        msg = detect_ceiling_violation("CEO will dispatch 7 sub-agents in parallel")
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("7", msg)
        self.assertIn("6", msg)

    def test_six_parallel_no_warning(self) -> None:
        msg = detect_ceiling_violation("Dispatch 6 sub-agents in parallel now")
        self.assertIsNone(msg)

    def test_twelve_parallel_triggers_warning(self) -> None:
        msg = detect_ceiling_violation("Dispatching 12 sub-agents in parallel batches")
        self.assertIsNotNone(msg)


class TestDecompositionAlgorithm(unittest.TestCase):
    def test_five_independent_items_recommends_parallel(self) -> None:
        items = [
            {"id": "a", "deps": [], "shared_files": ["staging/a/out.patch"]},
            {"id": "b", "deps": [], "shared_files": ["staging/b/out.patch"]},
            {"id": "c", "deps": [], "shared_files": ["staging/c/out.patch"]},
            {"id": "d", "deps": [], "shared_files": ["staging/d/out.patch"]},
            {"id": "e", "deps": [], "shared_files": ["staging/e/out.patch"]},
        ]
        dec = recommend_dispatch(items)
        self.assertEqual(dec["mode"], "parallel")
        self.assertEqual(dec["reason"], "parallel_chosen")
        self.assertEqual(dec["n"], 5)

    def test_single_chain_recommends_serial(self) -> None:
        items = [
            {"id": "a", "deps": []},
            {"id": "b", "deps": ["a"]},
            {"id": "c", "deps": ["b"]},
            {"id": "d", "deps": ["c"]},
        ]
        dec = recommend_dispatch(items)
        self.assertEqual(dec["mode"], "serial")
        self.assertEqual(dec["reason"], "serial_dependency_chain")

    def test_two_items_recommends_serial(self) -> None:
        items = [{"id": "a", "deps": []}, {"id": "b", "deps": []}]
        dec = recommend_dispatch(items)
        self.assertEqual(dec["mode"], "serial")
        self.assertEqual(dec["reason"], "serial_single_item")

    def test_eight_items_recommends_batched(self) -> None:
        items = [{"id": f"x{i}", "deps": []} for i in range(8)]
        dec = recommend_dispatch(items)
        self.assertEqual(dec["mode"], "batched")
        self.assertEqual(dec["batch_size"], 6)
        self.assertEqual(dec["n"], 8)

    def test_shared_file_contention_recommends_serial(self) -> None:
        items = [
            {"id": "a", "deps": [], "shared_files": ["foo.yaml"]},
            {"id": "b", "deps": [], "shared_files": ["foo.yaml"]},
            {"id": "c", "deps": [], "shared_files": ["other.yaml"]},
        ]
        dec = recommend_dispatch(items)
        self.assertEqual(dec["mode"], "serial")
        self.assertEqual(dec["reason"], "serial_shared_file_write")


class TestAuditEmitConvention(unittest.TestCase):
    def setUp(self) -> None:
        self.fm, self.body = _read_frontmatter(_resolve_skill_path())

    def test_audit_action_uses_snake_case_no_emit_suffix(self) -> None:
        action = self.fm.get("audit_action", "")
        self.assertIsInstance(action, str)
        self.assertTrue(action, "audit_action frontmatter field missing/empty")
        # Must match _lib/audit_emit.py _KNOWN_ACTIONS convention:
        # snake_case, no trailing _emit, no spaces, no dashes, lowercase.
        self.assertRegex(action, r"^[a-z][a-z0-9_]*$", f"bad action name: {action!r}")
        self.assertFalse(action.endswith("_emit"), f"must not end in _emit: {action!r}")
        # Per PLAN-083 §6 AC5c the expected name is exactly this:
        self.assertEqual(action, "parallelization_recommended")

    def test_audit_action_referenced_in_body(self) -> None:
        self.assertIn("parallelization_recommended", self.body)

    def test_audit_volume_budget_within_AC5c(self) -> None:
        # AC5c caps parallelization_by_default at <=50/hr; we publish the same.
        budget = self.fm.get("audit_volume_budget_per_hour", 0)
        self.assertIsInstance(budget, int)
        self.assertGreater(budget, 0)
        self.assertLessEqual(budget, 50)


if __name__ == "__main__":
    unittest.main()
