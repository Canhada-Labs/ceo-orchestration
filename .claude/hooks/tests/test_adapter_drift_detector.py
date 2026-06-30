"""Adapter drift detector.

PLAN-011 Phase 1 (§H2). Prevents silent contract drift between the
`NormalizedEvent` dataclass, the Claude adapter's field-population
sites, and `SPEC/v1/normalized_envelope.schema.md`.

## What this test enforces

1. Every field name in the `NormalizedEvent` dataclass appears in the
   SPEC's field inventory table.
2. Every field that the `claude` adapter populates via
   `NormalizedEvent(...)` call-sites is a known canonical field (no
   silently-introduced ones).
3. The SPEC-documented field inventory matches the dataclass
   one-to-one (no ghost fields in either direction).

If a PR introduces a new NormalizedEvent field without updating the
SPEC, this test fails CI. If the SPEC documents a field the dataclass
no longer has, same failure.

Per consensus S5, every test asserts ≥1 content behavior beyond exit
code (field names, SPEC table rows, dataclass members).
"""

from __future__ import annotations

import dataclasses
import re
import sys
import unittest
from pathlib import Path


from _lib import contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_FILE = REPO_ROOT / "SPEC" / "v1" / "normalized_envelope.schema.md"
CLAUDE_ADAPTER = REPO_ROOT / ".claude" / "hooks" / "_lib" / "adapters" / "claude.py"


def _dataclass_field_names() -> set:
    """Return the set of field names declared on NormalizedEvent."""
    return {f.name for f in dataclasses.fields(contract.NormalizedEvent)}


def _spec_inventory_fields() -> set:
    """Parse the §1.1 field inventory table out of the SPEC markdown.

    The table has this shape (one row per field):
        | `field_name` | `type` | ... | ... |
    Header rows (`| Field |`) and separator rows (`|---|`) are skipped.
    Backticks around the field name are stripped.
    """
    if not SPEC_FILE.exists():
        return set()
    text = SPEC_FILE.read_text(encoding="utf-8")
    names: set = set()

    # Match only rows whose first cell starts with `field_name` in backticks.
    # Row pattern: | `name` | `type` | ...
    row_re = re.compile(r"^\|\s*`([a-z_]+)`\s*\|", re.MULTILINE)
    for m in row_re.finditer(text):
        names.add(m.group(1))
    return names


def _claude_adapter_populated_fields() -> set:
    """Static-parse claude.py for keyword args passed to NormalizedEvent(...)."""
    if not CLAUDE_ADAPTER.exists():
        return set()
    source = CLAUDE_ADAPTER.read_text(encoding="utf-8")

    # Find each NormalizedEvent(...) call and extract kwarg names.
    # Claude adapter uses keyword arguments exclusively.
    populated: set = set()
    # Match `NormalizedEvent(` then balance parens to find the call-site body.
    call_sites = _find_call_sites(source, "NormalizedEvent(")
    for body in call_sites:
        # Parse top-level kwarg names: pattern `name=value,` where value
        # can itself contain nested parens / strings. We only need names,
        # so this regex matches an identifier followed by `=` at the
        # positions that are top-level in the call body.
        populated |= _top_level_kwarg_names(body)
    return populated


def _find_call_sites(source: str, head: str) -> list:
    """Return list of call-site body strings (between the matching parens)."""
    bodies = []
    i = 0
    while True:
        idx = source.find(head, i)
        if idx < 0:
            break
        start = idx + len(head)
        depth = 1
        in_str = None
        j = start
        while j < len(source) and depth > 0:
            ch = source[j]
            if in_str:
                if ch == "\\":
                    j += 2
                    continue
                if ch == in_str:
                    in_str = None
            else:
                if ch in ('"', "'"):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        if depth == 0:
            bodies.append(source[start:j])
            i = j + 1
        else:
            break
    return bodies


def _top_level_kwarg_names(body: str) -> set:
    """Extract kwarg names at top-level of a call body.

    We can't fully Python-parse without `ast`, but `ast.parse` on the
    whole source is cleaner — do that for robustness.
    """
    import ast
    # Wrap in a fake call for ast.parse: a(<body>)
    try:
        node = ast.parse("NormalizedEvent(" + body + ")", mode="eval")
    except SyntaxError:
        return set()
    if not isinstance(node.body, ast.Call):
        return set()
    return {kw.arg for kw in node.body.keywords if kw.arg is not None}


class TestDataclassFieldSet(TestEnvContext):
    """Lock the expected canonical field set on the dataclass side."""

    EXPECTED = {
        "session_id",
        "project",
        "phase",
        "tool_name",
        "tool_input",
        "tool_response",
        "description",
        "prompt",
        "subagent_type",
        "file_path",
        "old_string",
        "new_string",
        "replace_all",
        "command",
        # PLAN-125 WS-1 (kooky-harvest) — per-tool-call lifecycle scalars.
        # Named fields surfaced from the top-level payload (NOT via raw_payload).
        "tool_use_id",
        "duration_ms",
        "raw_payload",
        "parse_error",
    }

    def test_dataclass_exposes_exactly_expected_fields(self):
        actual = _dataclass_field_names()
        missing = self.EXPECTED - actual
        extra = actual - self.EXPECTED
        self.assertFalse(
            missing,
            "NormalizedEvent missing canonical fields: {}".format(sorted(missing)),
        )
        self.assertFalse(
            extra,
            "NormalizedEvent has extra fields not in EXPECTED "
            "(update SPEC + EXPECTED): {}".format(sorted(extra)),
        )

    def test_at_least_one_field_has_factory_default(self):
        """tool_input / tool_response / raw_payload use field(default_factory=dict).

        Assert so the drift detector catches anyone swapping them for a
        default mutable literal (common Python footgun).
        """
        factory_fields = {
            f.name
            for f in dataclasses.fields(contract.NormalizedEvent)
            if f.default_factory is not dataclasses.MISSING
        }
        self.assertIn("tool_input", factory_fields)
        self.assertIn("tool_response", factory_fields)
        self.assertIn("raw_payload", factory_fields)


class TestSpecInventoryMatchesDataclass(TestEnvContext):
    """The SPEC §1.1 field inventory table matches the dataclass."""

    def test_spec_file_exists(self):
        self.assertTrue(
            SPEC_FILE.exists(),
            "SPEC/v1/normalized_envelope.schema.md must exist",
        )

    def test_every_dataclass_field_documented_in_spec(self):
        spec_fields = _spec_inventory_fields()
        dc_fields = _dataclass_field_names()
        missing_in_spec = dc_fields - spec_fields
        self.assertFalse(
            missing_in_spec,
            "Dataclass fields not documented in SPEC: {}. "
            "Add rows to §1.1 of normalized_envelope.schema.md.".format(
                sorted(missing_in_spec),
            ),
        )

    def test_spec_does_not_document_fields_absent_from_dataclass(self):
        spec_fields = _spec_inventory_fields()
        dc_fields = _dataclass_field_names()
        ghost = spec_fields - dc_fields
        self.assertFalse(
            ghost,
            "SPEC documents fields absent from dataclass: {}. "
            "Remove from §1.1 or add to NormalizedEvent.".format(sorted(ghost)),
        )


class TestClaudeAdapterDrift(TestEnvContext):
    """Every field the Claude adapter populates is in the canonical set."""

    def test_claude_adapter_source_file_exists(self):
        self.assertTrue(CLAUDE_ADAPTER.exists(), "claude.py adapter file missing")

    def test_claude_adapter_populated_fields_are_canonical(self):
        populated = _claude_adapter_populated_fields()
        # Sanity: adapter should populate at least the key envelope fields.
        self.assertIn("session_id", populated)
        self.assertIn("tool_name", populated)
        # Every field claude.py writes must be known to the dataclass.
        dc_fields = _dataclass_field_names()
        rogue = populated - dc_fields
        self.assertFalse(
            rogue,
            "claude.py populates non-canonical fields: {}. "
            "Add them to NormalizedEvent + SPEC §1.1, or remove.".format(sorted(rogue)),
        )


if __name__ == "__main__":
    unittest.main()
