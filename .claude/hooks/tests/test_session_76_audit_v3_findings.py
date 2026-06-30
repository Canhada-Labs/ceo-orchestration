"""Tests for Session 76 Codex audit-v3 fixes (A / C / D).

These tests cover behavior that lands via the Owner-run
`OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh` script. The arbitration-kernel
HARD-DENY against `_lib/audit_emit.py` and `_lib/policy_preprocessors.py`
plus the sentinel guard against `check_plan_edit.py`,
`plan-edit.policy.yaml`, `install.sh`, and `SPEC/v1/*.md` mean the CEO
session cannot self-bypass — the Owner runs the ceremony with kernel
override + GPG-signed round-10 sentinel.

Tests are authored ahead of the ceremony so the validator block in the
ceremony script catches regressions; tests use `@unittest.skipUnless`
at class level (Session 75 lesson #2 — `skipTest()` in `setUp()` does
NOT call `tearDown()` and leaks env state across tests). Class-level
skip is the only safe form when fixtures touch env or filesystem.

Findings covered:
- **A** (DIM-04 #1) — `_KNOWN_ACTIONS` registers `skill_bootstrap_used`
  and `skill_bootstrap_post_hash`. `audit_emit._write_event` no longer
  drops bootstrap events. SPEC v2.15 schema bump.
- **C** (DIM-11) — `check_plan_edit.py._check_required_fields` enforces
  `refused_at` for `refused`, plus `reopen_via`, `reopen_trigger`, and
  body `## Reopen criteria` section for `done → executing` reopen, per
  ADR-092 honest-deferral. `policy_preprocessors` mirrors via 5 new
  derived fields and 5 new transition_reason_keys (byte-identity with
  YAML policy).
- **D** (DIM-19) — `scripts/install.sh` accepts `--verify-sigstore`
  as deprecated alias, emits stderr warning, and delegates to
  `--verify` semantics. SPEC `install-cli.md` documents the alias
  with `deprecated_in: 1.11.4` / `removed_in: 2.0.0`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Ceremony landing detectors — must match patch markers in
# OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh
# ---------------------------------------------------------------------------


def _is_audit_v3_ceremony_landed_A() -> bool:
    """True if `_KNOWN_ACTIONS` registers both bootstrap actions."""
    p = REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8")
    return (
        '"skill_bootstrap_used"' in text
        and '"skill_bootstrap_post_hash"' in text
    )


def _is_audit_v3_ceremony_landed_C() -> bool:
    """True if check_plan_edit.py has Session 76 audit-v3 enforcement."""
    p = REPO_ROOT / ".claude" / "hooks" / "check_plan_edit.py"
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8")
    return "Session 76 audit-v3" in text


def _is_audit_v3_ceremony_landed_D() -> bool:
    """True if install.sh has the deprecated --verify-sigstore alias."""
    p = REPO_ROOT / "scripts" / "install.sh"
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8")
    return "--verify-sigstore)" in text and "Session 76 audit-v3" in text


# ---------------------------------------------------------------------------
# Finding A — bootstrap actions registration
# ---------------------------------------------------------------------------


@unittest.skipUnless(
    _is_audit_v3_ceremony_landed_A(),
    "Audit-v3 finding A not yet landed — Owner must run OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh",
)
class Session76AuditV3FindingA(TestEnvContext):
    """`_KNOWN_ACTIONS` registers both bootstrap actions; emits land in JSONL."""

    def test_known_actions_contains_skill_bootstrap_used(self) -> None:
        # Re-import to pick up post-ceremony state.
        if "_lib.audit_emit" in sys.modules:
            del sys.modules["_lib.audit_emit"]
        from _lib import audit_emit  # noqa: F401
        self.assertIn(
            "skill_bootstrap_used",
            audit_emit._KNOWN_ACTIONS,
            "skill_bootstrap_used must be registered post-ceremony",
        )

    def test_known_actions_contains_skill_bootstrap_post_hash(self) -> None:
        if "_lib.audit_emit" in sys.modules:
            del sys.modules["_lib.audit_emit"]
        from _lib import audit_emit  # noqa: F401
        self.assertIn(
            "skill_bootstrap_post_hash",
            audit_emit._KNOWN_ACTIONS,
            "skill_bootstrap_post_hash must be registered post-ceremony",
        )

    def test_emit_generic_skill_bootstrap_used_writes_event(self) -> None:
        """Pre-fix: emit_generic('skill_bootstrap_used', ...) was dropped
        silently by `_write_event` because the action was unregistered.
        Post-fix: the event must land in the JSONL log.

        `TestEnvContext` already isolates the audit log path into its
        per-test tmpdir via `CEO_AUDIT_LOG_PATH`; we read that location
        directly rather than supplying our own.
        """
        if "_lib.audit_emit" in sys.modules:
            del sys.modules["_lib.audit_emit"]
        from _lib import audit_emit
        audit_emit.emit_generic(
            action="skill_bootstrap_used",
            skill_slug="test-skill",
            env_set=True,
            project="/t",
        )
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(
            log_path.is_file(),
            f"Expected audit-log.jsonl at {log_path} post-emit",
        )
        content = log_path.read_text(encoding="utf-8")
        found = False
        for line in content.splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("action") == "skill_bootstrap_used":
                found = True
                break
        self.assertTrue(
            found,
            "skill_bootstrap_used event must land in audit-log.jsonl",
        )

    def test_spec_audit_log_schema_lists_both_actions(self) -> None:
        """SPEC `audit-log.schema.md` must have rows for both new actions
        in the "Required fields per v2 action" table.
        """
        spec = REPO_ROOT / "SPEC" / "v1" / "audit-log.schema.md"
        text = spec.read_text(encoding="utf-8")
        self.assertIn(
            "`skill_bootstrap_used`",
            text,
            "SPEC must register skill_bootstrap_used row",
        )
        self.assertIn(
            "`skill_bootstrap_post_hash`",
            text,
            "SPEC must register skill_bootstrap_post_hash row",
        )

    def test_registry_drift_checker_passes_post_ceremony(self) -> None:
        """`check-audit-registry-coverage.py` must report exit 0 once both
        actions are registered. Pre-ceremony it fails because Session 76
        fix B (already landed) detects the orphans.
        """
        cmd = [
            sys.executable,
            str(REPO_ROOT / ".claude" / "scripts" / "check-audit-registry-coverage.py"),
            "--verbose",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"Registry checker MUST exit 0 post-ceremony but exited "
                f"{result.returncode}.\nstdout={result.stdout}\n"
                f"stderr={result.stderr}"
            ),
        )


# ---------------------------------------------------------------------------
# Finding C — Plan FSM ADR-092 enforcement
# ---------------------------------------------------------------------------


def _make_plan_text(
    *,
    status: str,
    fm_extra: Optional[dict] = None,
    body: str = "## Plan body\n\nContent.\n",
) -> str:
    """Build a plan markdown with frontmatter for testing."""
    lines = ["---", f"status: {status}"]
    for key, val in (fm_extra or {}).items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---\n")
    lines.append(body)
    return "\n".join(lines)


@unittest.skipUnless(
    _is_audit_v3_ceremony_landed_C(),
    "Audit-v3 finding C not yet landed — Owner must run OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh",
)
class Session76AuditV3FindingC(TestEnvContext):
    """check_plan_edit.py enforces ADR-092 fields for refused + reopen."""

    def setUp(self) -> None:
        super().setUp()
        # Force fresh module load post-ceremony.
        if "check_plan_edit" in sys.modules:
            del sys.modules["check_plan_edit"]
        import check_plan_edit  # noqa: F401
        self.mod = sys.modules["check_plan_edit"]

    def _decide(self, old_content: str, new_content: str) -> "self.mod.Decision":
        return self.mod._decide_on_buffers(old_content, new_content)

    # ----- refused branch — refused_at field -----

    def test_refused_without_refused_at_blocks(self) -> None:
        old = _make_plan_text(status="executing")
        new = _make_plan_text(
            status="refused",
            fm_extra={"refused_adr": "ADR-093"},  # missing refused_at
        )
        d = self._decide(old, new)
        self.assertFalse(d.allow)
        self.assertIn("refused_at", (d.reason or "").lower())

    def test_refused_with_both_fields_passes(self) -> None:
        old = _make_plan_text(status="executing")
        new = _make_plan_text(
            status="refused",
            fm_extra={
                "refused_adr": "ADR-093",
                "refused_at": "2026-04-29",
            },
        )
        d = self._decide(old, new)
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    # ----- reopen branch — done → executing -----

    def test_reopen_without_reopen_via_blocks(self) -> None:
        old = _make_plan_text(
            status="done",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        new = _make_plan_text(
            status="executing",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        d = self._decide(old, new)
        self.assertFalse(d.allow)
        self.assertIn("reopen_via", (d.reason or "").lower())

    def test_reopen_with_malformed_reopen_via_blocks(self) -> None:
        old = _make_plan_text(
            status="done",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        new = _make_plan_text(
            status="executing",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
                "reopen_via": "not-an-adr",  # malformed
            },
        )
        d = self._decide(old, new)
        self.assertFalse(d.allow)
        self.assertIn("reopen_via", (d.reason or "").lower())

    def test_reopen_without_reopen_trigger_blocks(self) -> None:
        old = _make_plan_text(
            status="done",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        new = _make_plan_text(
            status="executing",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
                "reopen_via": "ADR-092",  # missing reopen_trigger
            },
        )
        d = self._decide(old, new)
        self.assertFalse(d.allow)
        self.assertIn("reopen_trigger", (d.reason or "").lower())

    def test_reopen_without_reopen_criteria_section_blocks(self) -> None:
        old = _make_plan_text(
            status="done",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        new = _make_plan_text(
            status="executing",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
                "reopen_via": "ADR-092",
                "reopen_trigger": "external soak signal arrived",
            },
            body="## Plan body\n\nContent.\n",  # missing ## Reopen criteria
        )
        d = self._decide(old, new)
        self.assertFalse(d.allow)
        self.assertIn("reopen criteria", (d.reason or "").lower())

    def test_reopen_with_all_fields_passes(self) -> None:
        old = _make_plan_text(
            status="done",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
            },
        )
        new = _make_plan_text(
            status="executing",
            fm_extra={
                "completed_at": "2026-04-15",
                "related_commits": ["abc1234"],
                "reopen_via": "ADR-092",
                "reopen_trigger": "external soak signal arrived",
            },
            body=(
                "## Plan body\n\nContent.\n\n"
                "## Reopen criteria\n\n"
                "External signal X received from Y.\n"
            ),
        )
        d = self._decide(old, new)
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")


@unittest.skipUnless(
    _is_audit_v3_ceremony_landed_C(),
    "Audit-v3 finding C not yet landed — Owner must run OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh",
)
class Session76AuditV3FindingCByteIdentity(TestEnvContext):
    """policy_preprocessors derived fields mirror new check_plan_edit rules.

    Byte-identity between Python hook and YAML policy is enforced via
    test_byte_identity_harness.py + plan-edit.fixtures.jsonl. Here we
    spot-check that the derived field set has the new flags present.
    """

    def test_derived_plan_has_new_fields(self) -> None:
        if "_lib.policy_preprocessors" in sys.modules:
            del sys.modules["_lib.policy_preprocessors"]
        from _lib import policy_preprocessors as pp
        defaults = pp._plan_defaults()
        for field in (
            "refused_at_present",
            "reopen_via_present",
            "reopen_via_well_formed",
            "reopen_trigger_present",
            "reopen_criteria_section_present",
        ):
            self.assertIn(
                field,
                defaults,
                f"_plan_defaults must include '{field}' post-ceremony",
            )


# ---------------------------------------------------------------------------
# Finding D — install.sh --verify-sigstore deprecated alias
# ---------------------------------------------------------------------------


@unittest.skipUnless(
    _is_audit_v3_ceremony_landed_D(),
    "Audit-v3 finding D not yet landed — Owner must run OWNER-SESSION-76-AUDIT-V3-CEREMONY.sh",
)
class Session76AuditV3FindingD(TestEnvContext):
    """install.sh accepts --verify-sigstore as deprecated alias for --verify."""

    def test_install_sh_accepts_verify_sigstore_flag(self) -> None:
        """Calling `install.sh --verify-sigstore --dry-run /tmp/X` must
        not exit 1 due to unknown flag. We use --dry-run so no real install
        happens; preflight may still fail for missing tools but not on the
        flag itself.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_target = Path(tmp) / "target"
            tmp_target.mkdir()
            cmd = [
                "bash",
                str(REPO_ROOT / "scripts" / "install.sh"),
                "--verify-sigstore",
                "--dry-run",
                str(tmp_target),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            # Exit 1 specifically means "unknown flag" or user error.
            # A successful dry-run exit is 0; preflight failures are 3.
            # If exit is 1, the flag was rejected — that's the SemVer break.
            self.assertNotEqual(
                result.returncode,
                1,
                msg=(
                    f"install.sh --verify-sigstore must NOT exit 1 (unknown "
                    f"flag). stdout={result.stdout}\nstderr={result.stderr}"
                ),
            )

    def test_install_sh_emits_deprecation_warning_to_stderr(self) -> None:
        """Calling with --verify-sigstore must emit a deprecation warning
        on stderr containing 'deprecated' (case-insensitive)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_target = Path(tmp) / "target"
            tmp_target.mkdir()
            cmd = [
                "bash",
                str(REPO_ROOT / "scripts" / "install.sh"),
                "--verify-sigstore",
                "--dry-run",
                str(tmp_target),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertIn(
                "deprecated",
                result.stderr.lower(),
                msg=(
                    f"Expected 'deprecated' in stderr.\n"
                    f"stderr={result.stderr}"
                ),
            )

    def test_spec_install_cli_documents_deprecation(self) -> None:
        """SPEC must document the deprecation per its own §Deprecation
        contract: deprecated_in 1.11.4 + removed_in 2.0.0.
        """
        spec = REPO_ROOT / "SPEC" / "v1" / "install-cli.md"
        text = spec.read_text(encoding="utf-8")
        # Either an explicit deprecation block OR the alias documented under
        # §Flags with a deprecated marker — either suffices for SemVer.
        self.assertIn(
            "--verify-sigstore",
            text,
            "SPEC must mention --verify-sigstore (deprecated alias)",
        )
        self.assertIn(
            "deprecated_in",
            text,
            "SPEC §Deprecation must include deprecated_in field",
        )
        self.assertIn(
            "1.11.4",
            text,
            "SPEC must mark --verify-sigstore deprecated_in 1.11.4",
        )


if __name__ == "__main__":
    unittest.main()
