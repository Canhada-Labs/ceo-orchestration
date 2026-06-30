"""Tests for PLAN-063 Phase 4 round-1 ceremony — 7 audit-v3 backlog P2 fixes.

These tests assert the canonical patches LANDED via the Owner-run
`OWNER-SESSION-77-AUDIT-V3-BACKLOG-CEREMONY.sh` script. PLAN-063 closed
2026-05-01 (commit `4316cb8`); the ``CEO_PHASE_4_77_LANDED`` env-gate
that originally guarded these tests was removed in PLAN-066 Phase 1.2
per Round 1 finding U-CR-bare-pytest — the gate became dead code once
Phase 4 landed and was silently skipping 30 tests under bare pytest.

Findings covered (per PLAN-063 round-1 consensus):
- **DIM-01 P1** — install.sh comment narrative clarification (logic
  byte-identity preserved — Adjustment K).
- **DIM-02 P2** — SPEC plan.schema mirror update (`refused` terminal +
  `done → executing` reopen transition).
- **DIM-08 P2** — `_LEGAL_STATUSES` Python kernel-tier preserved
  (Adjustment K — YAML/SPEC consume via byte-identity test below).
- **DIM-12 #1** — ADR-071 status flip ACCEPTED → PROPOSED (per ADR-075
  §B+§F phantom-gate revert pending round-2 evidence).
- **DIM-12 #2** — `Enforcement commit:` field populated for ADR-{092,
  093, 095, 096, 097}.
- **DIM-20 #1** — actionlint.yml `continue-on-error: true → false`
  (hard-fail per Owner consensus); SHA-pin preserved.
- **DIM-20 #2** — governance-waivers.yaml consolidates rc_hold +
  workflow_staleness (per consensus S16); release.yml WAIVER_FILE
  path updated in 2 gates with awk-scoped greps; old
  rc-hold-waivers.yaml deleted via `git rm`.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Import TestEnvContext for env-hygiene compliance (test-env-hygiene
# allowlist scanner requires non-bare unittest.TestCase subclasses).
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# DIM-01 P1 — install.sh comment narrative clarification
# ---------------------------------------------------------------------------


class DIM01InstallShCommentClarification(TestEnvContext):
    """install.sh P0-15 comment block narrative is clarified; logic untouched."""

    def setUp(self) -> None:
        super().setUp()
        self.install_sh = REPO_ROOT / "scripts" / "install.sh"
        self.assertTrue(self.install_sh.is_file(), f"missing {self.install_sh}")
        self.body = self.install_sh.read_text(encoding="utf-8")

    def test_narrative_marker_present(self) -> None:
        """Idempotency marker present (only exists post-application)."""
        self.assertIn(
            "narrative clarified PLAN-063 DIM-01 P1, 2026-04-30",
            self.body,
            "DIM-01 narrative marker missing — Block 1 did not apply",
        )

    def test_source_tag_gpg_only_phrase(self) -> None:
        """New comment must contain the 'Source-tag = GPG-only' phrase."""
        self.assertIn(
            "Source-tag = GPG-only",
            self.body,
            "expected 'Source-tag = GPG-only' phrase in clarified comment",
        )

    def test_by_design_phrase(self) -> None:
        """New comment must contain the 'by design' clarification phrase."""
        self.assertIn(
            "by design",
            self.body,
            "expected 'by design' phrase in clarified comment",
        )

    def test_logic_self_sha_compute_intact(self) -> None:
        """`_self_sha_compute` function body MUST remain byte-identical (Adjustment K)."""
        # Anchor-based assertion: the function body's distinctive awk line is
        # present unchanged. (Full diff against a frozen baseline is overkill
        # given the comment-only-edit contract.)
        self.assertIn(
            "awk 'NR==FNR{n++; next} FNR < n'",
            self.body,
            "_self_sha_compute awk line altered — logic must be byte-identical",
        )

    def test_logic_verify_self_sha_intact(self) -> None:
        """`_verify_self_sha` function body MUST remain byte-identical."""
        self.assertIn(
            'CEO_INSTALL_SKIP_SELF_SHA',
            self.body,
            "_verify_self_sha env-var bypass altered — logic must be byte-identical",
        )
        self.assertIn(
            'PLACEHOLDER_RELEASE_FILL',
            self.body,
            "_verify_self_sha placeholder constant altered",
        )


# ---------------------------------------------------------------------------
# DIM-02 P2 — SPEC plan.schema lifecycle mirror
# ---------------------------------------------------------------------------


class DIM02SpecPlanSchemaMirror(TestEnvContext):
    """SPEC/v1/plan.schema.md mirrors the 6-state lifecycle + reopen transition."""

    def setUp(self) -> None:
        super().setUp()
        self.spec = REPO_ROOT / "SPEC" / "v1" / "plan.schema.md"
        self.assertTrue(self.spec.is_file(), f"missing {self.spec}")
        self.body = self.spec.read_text(encoding="utf-8")

    def test_refused_state_in_lifecycle(self) -> None:
        """`refused` terminal must be documented in the SPEC mirror."""
        self.assertIn(
            "`refused` terminal (per ADR-092)",
            self.body,
            "SPEC plan.schema must document `refused` terminal state",
        )

    def test_done_to_executing_reopen_documented(self) -> None:
        """Reopen transition `done → executing` documented per ADR-092."""
        self.assertIn(
            "`done → executing`",
            self.body,
            "SPEC plan.schema must document reopen transition",
        )

    def test_reopen_via_field_referenced(self) -> None:
        self.assertIn(
            "`reopen_via:`",
            self.body,
            "SPEC plan.schema must reference reopen_via: field",
        )

    def test_reopen_trigger_field_referenced(self) -> None:
        self.assertIn(
            "`reopen_trigger:`",
            self.body,
            "SPEC plan.schema must reference reopen_trigger: field",
        )


# ---------------------------------------------------------------------------
# DIM-08 P2 — _LEGAL_STATUSES byte-identity (Adjustment K)
# ---------------------------------------------------------------------------


class DIM08LegalStatusesByteIdentity(TestEnvContext):
    """Python kernel `_LEGAL_STATUSES` is unchanged; YAML/SPEC consume via this test."""

    EXPECTED = frozenset(
        {"abandoned", "done", "draft", "executing", "refused", "reviewed"}
    )

    def test_python_kernel_legal_statuses_unchanged(self) -> None:
        """Adjustment K: _LEGAL_STATUSES STAYS in Python kernel."""
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        try:
            # Re-import to pick up post-ceremony state.
            for mod in ("_lib.policy_preprocessors", "_lib"):
                if mod in sys.modules:
                    del sys.modules[mod]
            from _lib.policy_preprocessors import _LEGAL_STATUSES
        finally:
            try:
                sys.path.remove(str(REPO_ROOT / ".claude" / "hooks"))
            except ValueError:
                pass
        self.assertEqual(
            set(_LEGAL_STATUSES),
            set(self.EXPECTED),
            "_LEGAL_STATUSES drifted from canonical 6-state set",
        )

    def test_python_kernel_legal_statuses_is_frozenset(self) -> None:
        """PLAN-066 Phase 1.3 (Round 1 U-QA): kill ``frozenset → set``
        equivalent mutant. Set and frozenset compare equal element-wise,
        so a mutation flipping the type would pass the equality check
        above. This test asserts the actual type is frozenset (immutable
        — required to prevent accidental mutation by callers)."""
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        try:
            for mod in ("_lib.policy_preprocessors", "_lib"):
                if mod in sys.modules:
                    del sys.modules[mod]
            from _lib.policy_preprocessors import _LEGAL_STATUSES
        finally:
            try:
                sys.path.remove(str(REPO_ROOT / ".claude" / "hooks"))
            except ValueError:
                pass
        self.assertIsInstance(
            _LEGAL_STATUSES,
            frozenset,
            f"_LEGAL_STATUSES type drifted from frozenset to "
            f"{type(_LEGAL_STATUSES).__name__}; mutability is a bug",
        )

    def test_check_plan_edit_legal_statuses_matches(self) -> None:
        """check_plan_edit.py:_LEGAL_STATUSES must match policy_preprocessors."""
        check_path = REPO_ROOT / ".claude" / "hooks" / "check_plan_edit.py"
        self.assertTrue(check_path.is_file())
        body = check_path.read_text(encoding="utf-8")
        # The literal set spelling must include all 6 states.
        for state in self.EXPECTED:
            self.assertIn(
                f'"{state}"',
                body,
                f"check_plan_edit.py:_LEGAL_STATUSES missing '{state}'",
            )

    def test_spec_mentions_each_python_state(self) -> None:
        """SPEC mirror mentions all 6 Python states (set parity).

        Relaxed match: state name appears as word-boundary token anywhere
        in the SPEC body, not necessarily in its own backtick block.
        Block 2's NEW text uses a single backtick group for the
        `draft → reviewed → executing → done` transition chain plus
        individual backticks for `abandoned` + `refused` terminals;
        a strict ``f"`{state}`"`` check would reject the chain form.
        """
        import re
        spec_body = (REPO_ROOT / "SPEC" / "v1" / "plan.schema.md").read_text(
            encoding="utf-8"
        )
        for state in self.EXPECTED:
            self.assertRegex(
                spec_body,
                rf"\b{re.escape(state)}\b",
                f"SPEC plan.schema does not mention '{state}' state as a word",
            )

    # PLAN-066 DIM-08 closure — true byte-identity across 3 surfaces.
    # The 3 tests above only mention/match strings; these 2 parse the
    # YAML + SPEC representations and assert set equality with the
    # Python kernel source of truth.

    @staticmethod
    def _parse_yaml_legal_statuses() -> "frozenset[str]":
        """Parse `illegal_status_value:` template from plan-edit.policy.yaml.

        Format: ``"PLAN-LIFECYCLE: illegal status value. Must be one of:
        abandoned, done, draft, executing, refused, reviewed."``

        Returns the comma-separated state list as a frozenset.
        """
        import re
        yaml_path = REPO_ROOT / ".claude" / "policies" / "plan-edit.policy.yaml"
        body = yaml_path.read_text(encoding="utf-8")
        match = re.search(
            r"illegal_status_value:\s*\"[^\"]*Must be one of:\s*([^.\"]+)\.",
            body,
        )
        if not match:
            raise AssertionError(
                "plan-edit.policy.yaml: illegal_status_value template not "
                "matchable — DIM-08 parser drifted from canonical format"
            )
        states = [s.strip() for s in match.group(1).split(",")]
        return frozenset(s for s in states if s)

    @staticmethod
    def _parse_spec_legal_statuses() -> "frozenset[str]":
        """Parse Lifecycle line from SPEC/v1/plan.schema.md ## Summary block.

        Format: ``- Lifecycle state machine: `draft → reviewed →
        executing → done` + `abandoned` terminal + `refused` terminal``

        Structural parser (PLAN-066 Phase 1.1, Round 1 finding C2):
        no hardcoded keyword filter. Extracts the FIRST backtick group
        and splits on the arrow chain, plus any subsequent standalone
        backticks containing a single lowercase word. Tokens with `_`,
        `.`, or other non-alpha characters (e.g. `reopen_via:`,
        `check_plan_edit.py`) are excluded as non-state tokens —
        canonical lifecycle states are always single lowercase words.

        This catches a hypothetical 7th state (e.g. ``paused``) added
        to Python kernel + SPEC bidirectionally, without requiring the
        parser to be updated. The previous filter via
        ``state_keywords`` would silently drop new states.
        """
        import re
        spec_path = REPO_ROOT / "SPEC" / "v1" / "plan.schema.md"
        body = spec_path.read_text(encoding="utf-8")
        line_match = re.search(
            r"^- Lifecycle state machine:.*$",
            body,
            flags=re.MULTILINE,
        )
        if not line_match:
            raise AssertionError(
                "SPEC/v1/plan.schema.md: '- Lifecycle state machine:' line "
                "not found — DIM-08 parser drifted from canonical format"
            )
        line = line_match.group(0)
        groups = re.findall(r"`([^`]+)`", line)
        states: set = set()
        for group in groups:
            # Split chain backtick on arrow OR whitespace boundary.
            # Each fragment must be a single lowercase word [a-z]+
            # to qualify as a lifecycle state. Tokens with `_`, `.`,
            # `:`, digits, or uppercase are excluded (non-state
            # technical identifiers like `reopen_via:` or `ADR-092`).
            for fragment in re.split(r"[\s→]+", group.strip()):
                fragment = fragment.strip()
                if fragment and re.fullmatch(r"[a-z]+", fragment):
                    states.add(fragment)
        return frozenset(states)

    def test_yaml_policy_parses_to_python_kernel_set(self) -> None:
        """YAML illegal_status_value template parses to Python kernel set."""
        yaml_set = self._parse_yaml_legal_statuses()
        self.assertEqual(
            yaml_set,
            self.EXPECTED,
            f"YAML illegal_status_value template drifted from Python "
            f"kernel: yaml={sorted(yaml_set)} expected={sorted(self.EXPECTED)}",
        )

    def test_spec_summary_parses_to_python_kernel_set(self) -> None:
        """SPEC Lifecycle line parses to Python kernel set."""
        spec_set = self._parse_spec_legal_statuses()
        self.assertEqual(
            spec_set,
            self.EXPECTED,
            f"SPEC Lifecycle line drifted from Python kernel: "
            f"spec={sorted(spec_set)} expected={sorted(self.EXPECTED)}",
        )


# ---------------------------------------------------------------------------
# DIM-12 #1 — ADR-071 status flip ACCEPTED → PROPOSED
# ---------------------------------------------------------------------------


class DIM12Adr071StatusFlip(TestEnvContext):
    """ADR-071 line-4 status — promoted PROPOSED -> ACCEPTED at S147 (PLAN-109
    commit a3a4df2; historical accepted_at 2026-04-22 preserved). The original
    Session-77 audit-v3 DIM-12 contract pinned ADR-071 to PROPOSED on the
    expectation that a deferred round-1 ceremony would demote-and-restart it;
    S147's Codex MCP R2 review concluded promote was the correct doctrinal
    outcome and the demotion path was retired. Tests reversed to enforce the
    new contract: ADR-071 is ACCEPTED and stays ACCEPTED.
    """

    def setUp(self) -> None:
        super().setUp()
        self.adr_071 = (
            REPO_ROOT / ".claude" / "adr" / "ADR-071-benchmark-comparison-methodology.md"
        )
        self.assertTrue(self.adr_071.is_file(), f"missing {self.adr_071}")
        self.lines = self.adr_071.read_text(encoding="utf-8").splitlines()

    def test_status_accepted_on_line_4(self) -> None:
        """Frontmatter status field on line 4 must be ACCEPTED (post-S147)."""
        self.assertGreaterEqual(len(self.lines), 4, "ADR-071 truncated")
        self.assertEqual(
            self.lines[3].strip(),
            "status: ACCEPTED",
            f"expected 'status: ACCEPTED' on line 4; got '{self.lines[3]}'",
        )

    def test_no_lingering_proposed_in_frontmatter(self) -> None:
        """No `status: PROPOSED` literal lingering in the frontmatter block.

        Defense-in-depth post-S147 promotion — guards against accidental
        re-demote drift from a future Edit.
        """
        for i, line in enumerate(self.lines[:20]):
            if line.strip().startswith("status:"):
                self.assertNotIn(
                    "PROPOSED",
                    line,
                    f"residual 'status: PROPOSED' on line {i + 1}: '{line}'",
                )


# ---------------------------------------------------------------------------
# DIM-12 #2 — enforcement_commit field populated (5 ADRs)
# ---------------------------------------------------------------------------


class DIM12EnforcementCommitsPopulated(TestEnvContext):
    """5 ADR enforcement_commit fields populated per consensus."""

    def _read(self, name: str) -> str:
        p = REPO_ROOT / ".claude" / "adr" / name
        self.assertTrue(p.is_file(), f"missing {p}")
        return p.read_text(encoding="utf-8")

    def test_adr_092_has_wave_c_sha(self) -> None:
        body = self._read("ADR-092-plan-closure-honest-deferral.md")
        self.assertIn(
            "7b44042 (Wave C ceremony / v1.11.1 tag SHA)",
            body,
            "ADR-092 enforcement_commit not populated with Wave C SHA",
        )
        self.assertNotIn(
            "(Wave C ceremony commit — populated post-merge)",
            body,
            "ADR-092 still has placeholder enforcement_commit text",
        )

    def test_adr_093_documentation_only(self) -> None:
        body = self._read("ADR-093-refused-adr-moratorium.md")
        self.assertIn(
            "Documentation-only / no enforcement commit",
            body,
            "ADR-093 missing documentation-only enforcement_commit body",
        )
        self.assertIn(
            "60-day procedural moratorium ADR",
            body,
            "ADR-093 enforcement_commit body missing moratorium context",
        )

    def test_adr_095_documentation_only(self) -> None:
        body = self._read("ADR-095-calendar-gate-retraction.md")
        self.assertIn(
            "Documentation-only / no enforcement commit",
            body,
            "ADR-095 missing documentation-only enforcement_commit body",
        )
        self.assertIn(
            "calendar gate retraction is procedural",
            body,
            "ADR-095 enforcement_commit body missing procedural context",
        )

    def test_adr_096_documentation_only(self) -> None:
        body = self._read("ADR-096-vibecoder-only-by-design.md")
        self.assertIn(
            "Documentation-only / no enforcement commit",
            body,
            "ADR-096 missing documentation-only enforcement_commit body",
        )
        self.assertIn(
            "INSTALL.md banner",
            body,
            "ADR-096 enforcement_commit body missing INSTALL.md reference",
        )

    def test_adr_097_has_session_73_sha(self) -> None:
        body = self._read("ADR-097-function-length-advisory-permanent.md")
        self.assertIn(
            "54ff581 (Session 73 close-everything ceremony",
            body,
            "ADR-097 enforcement_commit not populated with Session 73 SHA",
        )


# ---------------------------------------------------------------------------
# DIM-20 #1 — actionlint.yml hard-mode + SHA-pin preserved
# ---------------------------------------------------------------------------


class DIM20ActionlintHardMode(TestEnvContext):
    """actionlint.yml continue-on-error: false + SHA-pin preserved."""

    def setUp(self) -> None:
        super().setUp()
        self.actionlint_yml = (
            REPO_ROOT / ".github" / "workflows" / "actionlint.yml"
        )
        self.assertTrue(self.actionlint_yml.is_file(), f"missing {self.actionlint_yml}")
        self.body = self.actionlint_yml.read_text(encoding="utf-8")

    def test_continue_on_error_false(self) -> None:
        """continue-on-error must be false (hard-fail) post round-1."""
        self.assertIn(
            "continue-on-error: false  # PLAN-063 DIM-20 #1",
            self.body,
            "actionlint.yml still in soft-fail mode (continue-on-error: true)",
        )

    def test_no_lingering_continue_on_error_true(self) -> None:
        """No residual YAML config `continue-on-error: true`.

        Scoped to YAML config lines (`continue-on-error:` at line start
        after whitespace), NOT to comment/docstring text mentioning
        the literal string for documentation purposes (lines 7 and 69
        of actionlint.yml mention it in `# **Mode:**` notes).
        """
        config_lines = [
            line for line in self.body.splitlines()
            if line.lstrip().startswith("continue-on-error:")
        ]
        for line in config_lines:
            self.assertNotIn(
                "true",
                line,
                f"actionlint.yml YAML config line still soft-fail: {line.strip()}",
            )

    def test_actions_checkout_sha_pinned(self) -> None:
        """actions/checkout SHA-pin preserved (Sprint 7 Dependabot pin)."""
        self.assertIn(
            "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
            self.body,
            "actions/checkout SHA-pin lost — defense-in-depth violation",
        )


# ---------------------------------------------------------------------------
# DIM-20 #2 — governance-waivers.yaml consolidation
# ---------------------------------------------------------------------------


class DIM20GovernanceWaiversConsolidation(TestEnvContext):
    """Old rc-hold-waivers.yaml deleted; new governance-waivers.yaml in place."""

    def setUp(self) -> None:
        super().setUp()
        self.old = REPO_ROOT / ".claude" / "governance" / "rc-hold-waivers.yaml"
        self.new = REPO_ROOT / ".claude" / "governance" / "governance-waivers.yaml"
        self.release_yml = REPO_ROOT / ".github" / "workflows" / "release.yml"

    def test_old_file_deleted(self) -> None:
        """rc-hold-waivers.yaml must be removed post-migration."""
        self.assertFalse(
            self.old.exists(),
            f"old waiver file still present: {self.old}",
        )

    def test_new_file_exists(self) -> None:
        self.assertTrue(
            self.new.is_file(),
            f"new consolidated waiver file missing: {self.new}",
        )

    def test_new_file_has_rc_hold_key(self) -> None:
        body = self.new.read_text(encoding="utf-8")
        # Top-level key, must start at column 0.
        self.assertTrue(
            any(line.rstrip("\n") == "rc_hold:" for line in body.splitlines()),
            "governance-waivers.yaml missing top-level rc_hold: key",
        )

    def test_new_file_has_workflow_staleness_key(self) -> None:
        body = self.new.read_text(encoding="utf-8")
        self.assertTrue(
            any(
                line.rstrip("\n") == "workflow_staleness:"
                for line in body.splitlines()
            ),
            "governance-waivers.yaml missing top-level workflow_staleness: key",
        )

    def test_release_yml_uses_new_path(self) -> None:
        """release.yml WAIVER_FILE points at governance-waivers.yaml in BOTH gates."""
        self.assertTrue(self.release_yml.is_file())
        body = self.release_yml.read_text(encoding="utf-8")
        # Two assertions: new path present (≥2 occurrences for both gates) and
        # old path absent.
        self.assertGreaterEqual(
            body.count('WAIVER_FILE=".claude/governance/governance-waivers.yaml"'),
            2,
            "release.yml should reference governance-waivers.yaml in BOTH gates",
        )
        self.assertNotIn(
            'WAIVER_FILE=".claude/governance/rc-hold-waivers.yaml"',
            body,
            "release.yml still references old rc-hold-waivers.yaml",
        )

    def test_release_yml_uses_awk_section_scoping(self) -> None:
        """release.yml greps must be section-scoped via awk per consensus S16.

        Codex re-pass residual #1 (Phase 9, 2026-05-01): assertion updated
        to match Phase 5b round-2 ceremony's flag-based parser (commit
        2d45add). Phase 4 round-1 originally introduced the section-
        scoping with the degenerate range pattern `awk '/^rc_hold:/,
        /^[a-z_]+:/'` (which collapses to 1 line — start matches end);
        Phase 5b corrected it to flag-based. Both Phase 4 + Phase 5b
        paired tests now consistently assert the FINAL state.
        """
        body = self.release_yml.read_text(encoding="utf-8")
        self.assertIn(
            "/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f",
            body,
            "release.yml RC-hold gate must use flag-based awk parser",
        )
        self.assertIn(
            "/^workflow_staleness:/{f=1; next} f && /^[a-z_]+:/{f=0} f",
            body,
            "release.yml workflow_staleness gate must use flag-based awk parser",
        )


# ---------------------------------------------------------------------------
# Always-runs: env hygiene (Adjustment F assertion)
# ---------------------------------------------------------------------------


_CEREMONY_IN_FLIGHT = os.environ.get("CEO_KERNEL_OVERRIDE_ACK") == "I-ACCEPT"


class CeremonyEnvHygiene(TestEnvContext):
    """Adjustment F — no CEO_KERNEL_OVERRIDE leak in test process env.

    These checks defend OUTSIDE-CEREMONY runs (developer terminal where
    a prior session leaked env vars). DURING the ceremony's in-flight
    test gate, the env vars are intentionally set (the bash script has
    not yet reached its post-test `unset` + final assertion). Skipping
    here when ceremony is in flight avoids a false-positive failure;
    the ceremony script's own bash assertion (post-unset) is the real
    Adjustment F enforcement gate.
    """

    @unittest.skipIf(
        _CEREMONY_IN_FLIGHT,
        "Ceremony in flight (CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT) — env "
        "hygiene enforced by ceremony script's post-unset bash assert.",
    )
    def test_ceo_kernel_override_not_set(self) -> None:
        self.assertNotIn(
            "CEO_KERNEL_OVERRIDE",
            os.environ,
            "CEO_KERNEL_OVERRIDE leaked into test process env (Adjustment F violation)",
        )

    @unittest.skipIf(
        _CEREMONY_IN_FLIGHT,
        "Ceremony in flight (CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT) — env "
        "hygiene enforced by ceremony script's post-unset bash assert.",
    )
    def test_ceo_kernel_override_ack_not_set(self) -> None:
        self.assertNotIn(
            "CEO_KERNEL_OVERRIDE_ACK",
            os.environ,
            "CEO_KERNEL_OVERRIDE_ACK leaked into test process env",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
