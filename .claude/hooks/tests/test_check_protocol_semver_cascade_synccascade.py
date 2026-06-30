"""PLAN-138 Wave D (ADR-156) — constitution sync-cascade tests.

Exercises the widened ``check_protocol_semver_cascade.py``:

- D.2: Sync Impact Report on BOTH the paired-amend path and the no-amend
  path; falsifiable drift (removing CLAUDE.md §Critical Rules marks item
  [1] MISSING/DRIFT — not a tautology).
- D.3: fail-open; kill-switch ``CEO_PROTOCOL_SYNC_CASCADE=0``; non-PROTOCOL
  payload performs ZERO dependent-set file reads (asserted via a
  read-counter monkeypatch, not just the ``{}`` output); clamp (a dependent
  file with newline+control char cannot forge an extra report line); sub-2s
  deadline respected.

Uses ``TestEnvContext`` from ``_lib/testing.py`` (env-hygiene gate: no bare
``os.environ[...]=``, no bare ``unittest.TestCase``). The hook module is
imported directly (via importlib against the LIVE hook path) so we can
instrument ``open`` reads + call internals; the public main() path is also
exercised in-process by feeding stdin and capturing stdout.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

# --- Locate repo root + the LIVE hook module, canonical-first. ---
_THIS = Path(__file__).resolve()
_repo_root: Optional[Path] = None
for _parent in _THIS.parents:
    if (_parent / ".claude" / "hooks" / "_lib").is_dir() and (
        _parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = _parent
        break
assert _repo_root is not None, "could not locate repo root from test path"

_HOOK_PATH = _repo_root / ".claude" / "hooks" / "check_protocol_semver_cascade.py"
_LIB_DIR = _repo_root / ".claude" / "hooks"

# Make _lib importable for TestEnvContext.
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_hook():
    """Load the hook module fresh (its module-level constants are read at
    call time, so a single load is fine for the whole suite)."""
    spec = importlib.util.spec_from_file_location(
        "_pscascade_under_test", str(_HOOK_PATH)
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_HOOK = _load_hook()


def _build_fixture_repo(root: Path, *, drop_critical_rules: bool = False,
                        inject_control_chars: bool = False) -> None:
    """Materialize a minimal repo whose dependent-set is all PRESENT,
    optionally dropping the CLAUDE.md §Critical Rules anchor (falsifiable
    drift) or injecting control chars into CLAUDE.md (clamp proof)."""
    (root / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "skills" / "core" / "ceo-orchestration").mkdir(
        parents=True, exist_ok=True
    )

    if drop_critical_rules:
        claude_body = "# CLAUDE.md\n\nno governance section here\n"
    elif inject_control_chars:
        # A newline + a forged-looking line + a NUL, all inside the matched
        # region. The sanitizer must strip these so no extra report line forms.
        claude_body = (
            "# CLAUDE.md\n## 5. Critical Rules\nINJECT\n  - FORGED: PRESENT\x00x\n"
        )
    else:
        claude_body = "# CLAUDE.md\n## 5. Critical Rules (dogfood mode)\nrules\n"
    (root / "CLAUDE.md").write_text(claude_body, encoding="utf-8")

    (root / ".claude" / "plans" / "PLAN-SCHEMA.md").write_text(
        "# PLAN-SCHEMA\n## 5. Required body sections\nbody\n", encoding="utf-8"
    )
    (root / ".claude" / "plans" / "DEBATE-SCHEMA.md").write_text(
        "# DEBATE-SCHEMA\nschema\n", encoding="utf-8"
    )
    (root / ".claude" / "skills" / "core" / "ceo-orchestration" / "SKILL.md").write_text(
        "---\nname: CEO Orchestration\ndescription: protocol reference\n---\n# body\n",
        encoding="utf-8",
    )
    (root / ".claude" / "scripts" / "validate-governance.sh").write_text(
        "#!/usr/bin/env bash\n# references PLAN-SCHEMA invariants\n", encoding="utf-8"
    )


def _run_main(payload: Dict, cwd: Path) -> Dict:
    """Drive the hook's main() in-process: feed stdin, capture stdout JSON.

    Sets CLAUDE_PROJECT_DIR to the fixture so the dependent-set probes hit
    the fixture, not the real repo. Returns the parsed stdout dict.
    """
    buf = io.StringIO()
    fake_stdin = io.StringIO(json.dumps(payload))
    with mock.patch.object(_HOOK.sys, "stdin", fake_stdin):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(cwd)}, clear=False):
            with redirect_stdout(buf):
                rc = _HOOK.main()
    out = buf.getvalue().strip()
    parsed = json.loads(out) if out else {}
    parsed["__rc__"] = rc  # type: ignore[index]
    return parsed


def _report_lines(parsed: Dict) -> List[str]:
    hso = parsed.get("hookSpecificOutput") or {}
    ac = hso.get("additionalContext") or ""
    return ac.split("\n")


class TestSyncCascade(TestEnvContext):
    """Constitution sync-cascade (PLAN-138 Wave D / ADR-156)."""

    # --- D.2: report on BOTH paths -------------------------------------

    def test_no_amend_path_emits_warn_and_report(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        lines = _report_lines(parsed)
        joined = "\n".join(lines)
        self.assertIn("WARN: PROTOCOL.md edit detected", joined)
        self.assertIn("Sync Impact Report", joined)
        # all 5 dependent items listed
        self.assertEqual(joined.count("PRESENT"), 6)  # 5 items + the count line "5/5 ... PRESENT"
        # never a decision
        self.assertNotIn("permissionDecision", joined)

    def test_paired_amend_path_still_emits_report_not_bare_brace(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [
                    {"file_path": ".claude/adr/ADR-115-AMEND-1.md"},
                ],
            },
        }
        parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        joined = "\n".join(_report_lines(parsed))
        # The pre-PLAN-138 behavior returned bare {}. Now the report ships.
        self.assertIn("Sync Impact Report", joined)
        # The legacy WARN must NOT appear on the paired-amend path.
        self.assertNotIn("WARN: PROTOCOL.md edit detected", joined)
        self.assertNotIn("permissionDecision", joined)

    # --- D.2: falsifiable drift (NOT a tautology) ----------------------

    def test_falsifiable_drift_marks_missing_critical_rules(self):
        repo = self.project_dir
        _build_fixture_repo(repo, drop_critical_rules=True)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        parsed = _run_main(payload, repo)
        joined = "\n".join(_report_lines(parsed))
        # item [1] must read MISSING/DRIFT, proving the detector is falsifiable.
        crit = [ln for ln in _report_lines(parsed) if "Critical Rules" in ln]
        self.assertTrue(crit, "Critical Rules item missing from report")
        self.assertIn("MISSING/DRIFT", crit[0])
        # the count line must now read 4/5, not 5/5
        self.assertIn("4/5", joined)

    def test_all_present_when_anchors_intact(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        joined = "\n".join(_report_lines(_run_main(payload, repo)))
        self.assertIn("5/5", joined)
        self.assertNotIn("MISSING/DRIFT", joined)

    # --- D.3: kill-switch ----------------------------------------------

    def test_kill_switch_suppresses_report_on_paired_amend(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [{"file_path": ".claude/adr/ADR-115-AMEND-1.md"}],
            },
        }
        with mock.patch.dict(os.environ, {"CEO_PROTOCOL_SYNC_CASCADE": "0"}, clear=False):
            parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        # report suppressed → bare {} on the paired-amend path
        self.assertEqual(parsed.get("hookSpecificOutput"), None)
        self.assertNotIn("permissionDecision", json.dumps(parsed))

    def test_kill_switch_keeps_legacy_warn_on_no_amend(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        with mock.patch.dict(os.environ, {"CEO_PROTOCOL_SYNC_CASCADE": "0"}, clear=False):
            parsed = _run_main(payload, repo)
        joined = "\n".join(_report_lines(parsed))
        self.assertIn("WARN: PROTOCOL.md edit detected", joined)
        self.assertNotIn("Sync Impact Report", joined)

    # --- D.3: non-PROTOCOL zero-read (counter, not just {}) ------------

    def test_non_protocol_edit_performs_zero_dependent_reads(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/some_module.py"},
        }
        # Instrument the hook's dependent-set reader: it MUST NOT be called.
        with mock.patch.object(_HOOK, "_read_head") as read_spy:
            parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        # bare {} output
        self.assertEqual(parsed.get("hookSpecificOutput"), None)
        # the load-bearing assertion: ZERO dependent-set reads on the hot path
        self.assertEqual(read_spy.call_count, 0)

    def test_protocol_edit_does_read_dependent_set(self):
        """Counter-test: a PROTOCOL.md edit DOES read the dependent set
        (so the zero-read assertion above is meaningful, not vacuous)."""
        repo = self.project_dir
        _build_fixture_repo(repo)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        real_read = _HOOK._read_head
        with mock.patch.object(_HOOK, "_read_head", side_effect=real_read) as read_spy:
            _run_main(payload, repo)
        self.assertGreater(read_spy.call_count, 0)

    # --- D.3: clamp (control char cannot forge a line) -----------------

    def test_clamp_blocks_forged_report_line(self):
        repo = self.project_dir
        _build_fixture_repo(repo, inject_control_chars=True)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        parsed = _run_main(payload, repo)
        lines = _report_lines(parsed)
        # No line may be a forged "FORGED: PRESENT" entry — the report only
        # ever renders our closed-set labels. The matched text is never echoed,
        # and even if a label were attacker-influenced the sanitizer strips
        # newlines/control chars so the line count cannot grow.
        forged = [ln for ln in lines if "FORGED" in ln]
        self.assertEqual(forged, [])
        # Critical Rules anchor is still PRESENT (the "## 5. Critical Rules" head matched)
        crit = [ln for ln in lines if "Critical Rules" in ln]
        self.assertTrue(crit)
        self.assertIn("PRESENT", crit[0])

    def test_sanitize_path_strips_control_and_clamps(self):
        dirty = "abc\n\x00\x07def" + ("z" * 500)
        cleaned = _HOOK._sanitize_path(dirty)
        self.assertNotIn("\n", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertLessEqual(len(cleaned), _HOOK._FRAGMENT_CLAMP)

    # --- D.3: deadline --------------------------------------------------

    def test_deadline_respected_marks_indeterminate_and_returns_fast(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        # An already-expired deadline → the verify loop must short-circuit
        # to INDETERMINATE without reading every file, and never hang.
        past = time.monotonic() - 1.0
        t0 = time.monotonic()
        findings = _HOOK._verify_dependent_set(repo, past)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 1.0)
        self.assertTrue(findings)
        # everything past the blown deadline is INDETERMINATE
        self.assertTrue(all(st == "INDETERMINATE" for _, st in findings))

    def test_within_budget_completes_under_two_seconds(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        deadline = time.monotonic() + _HOOK.TIME_BUDGET_S
        t0 = time.monotonic()
        findings = _HOOK._verify_dependent_set(repo, deadline)
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(len(findings), 5)

    # --- fail-open: garbage/binary dependent file ----------------------

    def test_fail_open_on_binary_dependent_file(self):
        repo = self.project_dir
        _build_fixture_repo(repo)
        # Make CLAUDE.md a binary blob: probe must degrade, never crash.
        (repo / "CLAUDE.md").write_bytes(b"\x00\x01\x02\xff\xfe" * 1000)
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        # binary file → the "Critical Rules" substring is absent → MISSING/DRIFT
        # (read succeeds with errors='replace'); the hook never crashes.
        joined = "\n".join(_report_lines(parsed))
        self.assertIn("Sync Impact Report", joined)

    def test_fail_open_when_dependent_dir_absent(self):
        repo = self.project_dir
        # Do NOT build the fixture — none of the dependent files exist.
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        parsed = _run_main(payload, repo)
        self.assertEqual(parsed["__rc__"], 0)
        joined = "\n".join(_report_lines(parsed))
        # all unreadable → INDETERMINATE, never an error / crash
        self.assertIn("INDETERMINATE", joined)
        self.assertNotIn("permissionDecision", joined)


if __name__ == "__main__":
    unittest.main()
