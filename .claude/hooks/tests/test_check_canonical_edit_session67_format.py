"""PLAN-044 audit-v2 C6-P0-04 — Scope: parser handles Session 67 format.

The Session 67 mega-sentinel `Scope (24 canonical paths):` format with
categorized sub-headers and blank lines between bullet groups was NOT
parsed by the original regex `^Scope:\\s*\\n((?:\\s*-\\s*\\S+.*\\n?)+)`.
This caused 9 ADR canonical-edit attempts to silently fall through to
older sentinels (PLAN-050 round-17 etc.), leaving the 9 ADRs in
PROPOSED state on disk despite the mega-ceremony narrative claiming
ACCEPTED.

Wave A ships a backwards-compatible parser. These tests prove:

1. Format A (legacy contiguous bullet list) still works.
2. Format B (Session 67 categorized with `Scope (N):` header + sub-
   sections + blank lines) parses correctly.
3. Top-level terminators stop the Scope block (Effective:, Plans:,
   Rationale, etc.).
4. Sub-section headers within Scope are skipped, not treated as
   terminators.
5. Markdown horizontal rule (`---`) terminates the block.

Tests run against the LIVE hook via subprocess (per existing pattern in
test_check_canonical_edit.py). They will be RED at HEAD until Wave A
ceremony promotes the staged parser fix to canonical
.claude/hooks/check_canonical_edit.py. Once promoted, they go GREEN
and join the standard pytest run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_canonical_edit.py"


# Session 67 mega-sentinel canonical fixture, verbatim modulo the
# Approved-By line which we substitute with the test plan-id.
_SESSION_67_FIXTURE = """\
# Session 67 D5 mega-sentinel — close-everything ceremony

Approved-By: @testowner deadbeef

Scope (24 canonical paths):

ADR canonical promotions (9 files, all from staging):
- .claude/adr/ADR-083-mcp-injection-scanner.md
- .claude/adr/ADR-084-multi-adapter-refused-claude-only.md
- .claude/adr/ADR-085-framework-landscape-claude-only.md

Hook code (PLAN-052):
- .claude/hooks/_lib/mcp_injection_scan.py
- .claude/hooks/check_mcp_response.py

SPEC additions:
- SPEC/v1/audit-log.schema.md

Rationale: This is the close-everything ceremony for Owner directive.
"""

_LEGACY_FIXTURE = """\
# Architect Round-17 Approval — PLAN-050 Sprint 31 Deep Closure

Approved-By: @testowner bbad8d7

Scope:
  - .claude/adr/ADR-049a-worktree-orchestration-policy.md
  - .claude/hooks/_lib/secret_patterns.py

Effective: 2026-04-22
"""

_HR_FIXTURE = """\
# Architect Round-99 Approval

Approved-By: @testowner cafef00d

Scope:
  - .claude/adr/ADR-100-test.md

---

Some unrelated content below the HR.
"""


class CheckCanonicalEditSession67FormatTest(TestEnvContext):
    """End-to-end subprocess tests against the live hook."""

    def _invoke(self, payload: dict) -> tuple[int, str, str]:
        env = {**os.environ}
        # PLAN-086 Wave I.1 (ADR-119) tightened the env-override regex to
        # ^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$. Older uppercase
        # "PLAN-044-AUDIT-V2-WAVE-A" fails the new lowercase pattern.
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-044-audit-v2-wave-a")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _write_sentinel(
        self,
        plan_id: str,
        round_n: int,
        content: str,
    ) -> Path:
        sentinel_dir = (
            self.project_dir / ".claude" / "plans" / plan_id /
            "architect" / f"round-{round_n}"
        )
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        sentinel = sentinel_dir / "approved.md"
        sentinel.write_text(content, encoding="utf-8")
        return sentinel

    def _write_canonical_target(self, rel: str) -> Path:
        full = self.project_dir / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("placeholder", encoding="utf-8")
        return full

    def test_session67_format_first_section_grant(self) -> None:
        """Path in the first sub-section of a Session 67-format Scope."""
        self._write_sentinel("PLAN-067", 1, _SESSION_67_FIXTURE)
        target = self._write_canonical_target(
            ".claude/adr/ADR-083-mcp-injection-scanner.md"
        )
        rc, out, _err = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_session67_format_second_section_grant(self) -> None:
        """Path in the SECOND sub-section after blank line + sub-header."""
        self._write_sentinel("PLAN-067", 1, _SESSION_67_FIXTURE)
        target = self._write_canonical_target(
            ".claude/hooks/check_mcp_response.py"
        )
        rc, out, _err = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(out).get("decision", "allow"), "allow",
            f"second sub-section path must parse; got {out!r}",
        )

    def test_session67_format_third_section_grant(self) -> None:
        """SPEC path in the THIRD sub-section."""
        self._write_sentinel("PLAN-067", 1, _SESSION_67_FIXTURE)
        target = self._write_canonical_target("SPEC/v1/audit-log.schema.md")
        rc, out, _err = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_session67_format_path_after_rationale_terminator_blocked(
        self,
    ) -> None:
        """A path mentioned ONLY after `Rationale:` must NOT be granted."""
        fixture_with_extra = _SESSION_67_FIXTURE.replace(
            "Rationale: This is the close-everything ceremony for Owner directive.\n",
            "Rationale: blah\n- .claude/adr/ADR-999-not-granted.md\n",
        )
        self._write_sentinel("PLAN-067", 2, fixture_with_extra)
        target = self._write_canonical_target(
            ".claude/adr/ADR-999-not-granted.md"
        )
        rc, out, _err = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(out)["decision"], "block",
            "path mentioned only after Rationale terminator must be blocked",
        )

    def test_legacy_plan050_format_still_grants(self) -> None:
        """Format A regression: PLAN-050 round-17 plain `Scope:` still works."""
        self._write_sentinel("PLAN-050b", 17, _LEGACY_FIXTURE)
        target = self._write_canonical_target(
            ".claude/adr/ADR-049a-worktree-orchestration-policy.md"
        )
        rc, out, _err = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_horizontal_rule_terminates_scope(self) -> None:
        """Markdown HR (---) must terminate the Scope block."""
        fixture_post_hr = _HR_FIXTURE.replace(
            "Some unrelated content below the HR.",
            "- .claude/adr/ADR-101-not-granted.md",
        )
        self._write_sentinel("PLAN-099", 1, fixture_post_hr)
        target_granted = self._write_canonical_target(
            ".claude/adr/ADR-100-test.md"
        )
        target_blocked = self._write_canonical_target(
            ".claude/adr/ADR-101-not-granted.md"
        )
        rc1, out1, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target_granted)},
        })
        rc2, out2, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target_blocked)},
        })
        self.assertEqual(rc1, 0)
        self.assertEqual(json.loads(out1).get("decision", "allow"), "allow")
        self.assertEqual(rc2, 0)
        self.assertEqual(
            json.loads(out2)["decision"], "block",
            "path after --- HR must NOT be granted",
        )


if __name__ == "__main__":
    unittest.main()
