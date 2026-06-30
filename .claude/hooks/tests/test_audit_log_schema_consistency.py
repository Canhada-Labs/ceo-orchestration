"""SPEC-vs-code consistency tests for audit-log schema enums.

Closes Session 75 Codex Finding 6: SPEC v1 audit-log.schema.md declared
`scanner_action` enum `{advisory, stripped, blocked}` and `severity`
enum `{low, medium, high}`, but `check_mcp_response.py:188` (Session 73)
emitted `scanner_action="block"` (verb form, not in SPEC) and
`_lib/audit_emit.py:2179` docstring claimed severity `info|warn|block`
(also not in SPEC). Both drift directions caught by Codex external
review; this test prevents recurrence.

Strategy:
- Parse SPEC schema action table for enum fields.
- Read code for the literal strings emitted/documented for those fields.
- Fail loudly if any code-side string is not a member of the SPEC enum.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SPEC_FILE = REPO_ROOT / "SPEC" / "v1" / "audit-log.schema.md"
SCAN_FILE = REPO_ROOT / ".claude" / "hooks" / "_lib" / "mcp_injection_scan.py"
CHECK_FILE = REPO_ROOT / ".claude" / "hooks" / "check_mcp_response.py"


def _extract_spec_enum(field: str) -> set:
    """Return the literal enum members for ``field`` in
    ``mcp_injection_finding`` row of the SPEC table."""
    text = SPEC_FILE.read_text(encoding="utf-8")
    row = next(
        (line for line in text.splitlines() if "`mcp_injection_finding`" in line),
        None,
    )
    assert row, "mcp_injection_finding row missing from SPEC schema table"
    pattern = rf"`{field}`\s*\(enum\s*`\{{([^}}]+)\}}`\)"
    m = re.search(pattern, row)
    assert m, f"{field} enum block not found in SPEC row"
    return {tok.strip() for tok in m.group(1).split(",") if tok.strip()}


class SpecConsistencyTest(TestEnvContext):
    """Code-emitted scanner_action and severity values must be in SPEC enum."""

    def test_scanner_action_enum_matches_spec(self) -> None:
        spec_enum = _extract_spec_enum("scanner_action")
        self.assertEqual(spec_enum, {"advisory", "stripped", "blocked"})

        # Code emits two literal scanner_action values: the strict-block
        # branch and the non-block branch.
        check_text = CHECK_FILE.read_text(encoding="utf-8")
        m = re.search(
            r'scanner_action\s*=\s*"([^"]+)"\s+if\s+will_block\s+else\s+"([^"]+)"',
            check_text,
        )
        self.assertIsNotNone(
            m,
            "expected ternary `scanner_action = '<a>' if will_block else '<b>'` "
            "in check_mcp_response.py",
        )
        emitted = {m.group(1), m.group(2)}
        unknown = emitted - spec_enum
        self.assertFalse(
            unknown,
            f"check_mcp_response.py emits scanner_action values not in SPEC enum: {unknown}",
        )

    def test_severity_enum_matches_classify_returns(self) -> None:
        spec_enum = _extract_spec_enum("severity")
        self.assertEqual(spec_enum, {"low", "medium", "high"})

        # _SEVERITY_BY_FAMILY values + literal "low" fallback in classify().
        scan_text = SCAN_FILE.read_text(encoding="utf-8")
        m = re.search(
            r"_SEVERITY_BY_FAMILY:\s*Dict\[str,\s*str\]\s*=\s*\{([^}]+)\}",
            scan_text,
        )
        self.assertIsNotNone(m, "_SEVERITY_BY_FAMILY block missing")
        body = m.group(1)
        family_severities = set(re.findall(r'"\s*([a-z]+)\s*"\s*,\s*#?', body))
        # The family key strings get matched too — filter to severity tokens.
        severity_tokens = family_severities & {"low", "medium", "high", "critical", "info", "warn", "block"}
        self.assertTrue(severity_tokens, "no severity tokens parsed from _SEVERITY_BY_FAMILY")
        unknown = severity_tokens - spec_enum
        self.assertFalse(
            unknown,
            f"_SEVERITY_BY_FAMILY contains severity values not in SPEC enum: {unknown}",
        )


if __name__ == "__main__":
    unittest.main()
