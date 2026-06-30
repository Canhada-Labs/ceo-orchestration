"""Unit tests for ``.claude/scripts/reality-ledger.py``.

PLAN-071 §4.3 Phase 2 deliverable. Covers:
  - Detector #1 runtime_read_missing (AST-level + cosmetic-mention filter)
  - Detector #2 installable_claim_drift (placeholder marker)
  - Detector #3 model_assignment_divergence (audit-log majority diff)
  - Detector #4 enforcement_commit_unpopulated (ADR-067 ground truth)
  - Detector #6 audit_action_phantom (Codex S76 precedent shape)
  - Output rendering contract: markdown vs json/jsonl key sets
  - Redaction: `sk-test-...` → `[API_KEY]`
  - Audit emission allowlist + scrub
  - CLI exit-code contract (0 = ran, 2 = error)
  - Self-exclusion (task-route.py / reality-ledger.py / owner-ceremony/archive)

Total: ≥30 tests + ≥10 redaction/contract scrub tests.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "reality-ledger.py"
HOOKS_LIB = REPO_ROOT / ".claude" / "hooks"
FIXTURES = REPO_ROOT / ".claude" / "scripts" / "tests" / "fixtures" / "reality-ledger"

if str(HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(HOOKS_LIB))


def _load_module():
    spec = importlib.util.spec_from_file_location("reality_ledger", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rl():
    return _load_module()


# ---------------------------------------------------------------------------
# Module-level structural tests
# ---------------------------------------------------------------------------

def test_module_loads(rl):
    assert rl.SCHEMA_VERSION == "reality-ledger-finding.v1"


def test_detector_registry_has_6_active(rl):
    # Plan §4.3: 5 active detectors v1.14.0; #5 deferred. PLAN-078 Wave 2
    # adds detector #7 estimate_drift → 6 active total.
    assert len(rl.DETECTOR_REGISTRY) == 6
    assert "runtime_read_missing" in rl.DETECTOR_REGISTRY
    assert "installable_claim_drift" in rl.DETECTOR_REGISTRY
    assert "model_assignment_divergence" in rl.DETECTOR_REGISTRY
    assert "enforcement_commit_unpopulated" in rl.DETECTOR_REGISTRY
    assert "audit_action_phantom" in rl.DETECTOR_REGISTRY
    assert "estimate_drift" in rl.DETECTOR_REGISTRY  # PLAN-078 Wave 2
    assert "default_flip_orphan" not in rl.DETECTOR_REGISTRY  # deferred


def test_finding_allowlist_is_frozenset(rl):
    assert isinstance(rl._REALITY_LEDGER_FINDING_ALLOWLIST, frozenset)
    # confidence_bps replaces float "confidence" (CanonicalJsonError fix).
    expected = {
        "action", "ts", "detector", "severity", "confidence_bps",
        "claim_source_sha256", "finding_count_in_run",
    }
    assert set(rl._REALITY_LEDGER_FINDING_ALLOWLIST) == expected


def test_self_exclude_basenames_includes_both_scripts(rl):
    assert "task-route.py" in rl.SELF_EXCLUDE_BASENAMES
    assert "reality-ledger.py" in rl.SELF_EXCLUDE_BASENAMES


def test_markdown_only_fields_excludes_path(rl):
    assert "claim_source_path" in rl._MARKDOWN_ONLY_FIELDS


# ---------------------------------------------------------------------------
# Detector #1 — runtime_read_missing (AST-level)
# ---------------------------------------------------------------------------

def test_detector_1_positive_fixture(rl):
    """Documented but not read at AST level → finding."""
    findings = rl.detect_runtime_read_missing(
        repo_root=FIXTURES / "detector-1-positive",
        explicit_env_vars=["CEO_DETECTOR_1_TEST"],
    )
    assert len(findings) == 1
    f = findings[0]
    assert f["detector"] == "runtime_read_missing"
    assert f["_extra"]["env_var"] == "CEO_DETECTOR_1_TEST"


def test_detector_1_negative_fixture(rl):
    """Documented AND read via os.environ.get / os.getenv / subprocess.run."""
    findings = rl.detect_runtime_read_missing(
        repo_root=FIXTURES / "detector-1-negative",
        explicit_env_vars=["CEO_DETECTOR_1_OK"],
    )
    assert findings == []


def test_detector_1_boundary_excludes_common_tokens(rl):
    """HTTP/JSON/TODO etc. should not be classified as env vars.

    These are in the EXCLUDE set per `_is_plausible_env_var`. Note that
    `MY_VAR` (6-char + underscore) IS plausible by design — only the
    above common-protocol/keyword tokens are excluded.
    """
    findings = rl.detect_runtime_read_missing(
        repo_root=FIXTURES / "detector-1-boundary",
    )
    survived = {f["_extra"].get("env_var") for f in findings}
    assert survived & {"HTTP", "JSON", "TODO"} == set()


def test_detector_1_reproduces_ceo_model_downshift_at_head(rl):
    """Acceptance: detector #1 finds (or no longer finds) CEO_MODEL_DOWNSHIFT.

    PLAN-067 shipped and CEO_MODEL_DOWNSHIFT is now wired in the codebase,
    so the detector correctly returns zero findings (the var IS read at
    runtime).  The fixture pin is updated accordingly:
    - pre-PLAN-067: assert len == 1 (unwired gap detected)
    - post-PLAN-067 (current HEAD): assert len == 0 (gap closed)

    If CEO_MODEL_DOWNSHIFT ever becomes unwired again, this test will fail
    loudly — keeping the explicit-var fixture pin semantics intact.
    """
    findings = rl.detect_runtime_read_missing(
        repo_root=REPO_ROOT,
        explicit_env_vars=["CEO_MODEL_DOWNSHIFT"],
    )
    assert len(findings) == 0, (
        "CEO_MODEL_DOWNSHIFT was wired in PLAN-067 — detector must return "
        "zero findings at HEAD.  If it was later un-wired, update this "
        "fixture pin deliberately (silent-drift→loud-fail)."
    )


def test_detector_1_ast_skips_comments_and_docstrings(rl):
    """Mentions inside comments/docstrings must NOT count as a read."""
    # The fixture's sample.py has 'CEO_DETECTOR_1_TEST' in a comment but
    # reads SOMETHING_ELSE. Detector must still report a positive.
    findings = rl.detect_runtime_read_missing(
        repo_root=FIXTURES / "detector-1-positive",
        explicit_env_vars=["CEO_DETECTOR_1_TEST"],
    )
    assert len(findings) == 1


def test_detector_1_detects_subprocess_env_form(rl):
    """subprocess.run(env={'VAR': ...}) must count as a read."""
    findings = rl.detect_runtime_read_missing(
        repo_root=FIXTURES / "detector-1-negative",
        explicit_env_vars=["CEO_DETECTOR_1_OK"],
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Detector #2 — installable_claim_drift
# ---------------------------------------------------------------------------

def test_detector_2_positive_fixture(rl):
    findings = rl.detect_installable_claim_drift(
        repo_root=FIXTURES / "detector-2-positive",
    )
    assert len(findings) == 1
    assert findings[0]["detector"] == "installable_claim_drift"
    assert "PLACEHOLDER" in findings[0]["_extra"]["markers"]


def test_detector_2_negative_fixture(rl):
    findings = rl.detect_installable_claim_drift(
        repo_root=FIXTURES / "detector-2-negative",
    )
    assert findings == []


def test_detector_2_boundary_no_lockfile(rl):
    """No lockfile → silent zero-finding (not error)."""
    findings = rl.detect_installable_claim_drift(
        repo_root=FIXTURES / "detector-2-boundary",
    )
    assert findings == []


def test_detector_2_reproduces_real_requirements_lock(rl):
    """Acceptance: real .claude/rag/requirements.lock at HEAD is a placeholder."""
    findings = rl.detect_installable_claim_drift(repo_root=REPO_ROOT)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


# ---------------------------------------------------------------------------
# Detector #3 — model_assignment_divergence
# ---------------------------------------------------------------------------

def test_detector_3_positive_fixture(rl):
    findings = rl.detect_model_assignment_divergence(
        repo_root=FIXTURES / "detector-3-positive",
        audit_log_path=FIXTURES / "detector-3-positive" / "audit-log.jsonl",
    )
    assert len(findings) == 1
    f = findings[0]
    assert f["_extra"]["claim"] == "claude-haiku-4-7"
    assert f["_extra"]["observed"] == "claude-sonnet-4-6"


def test_detector_3_negative_fixture(rl):
    findings = rl.detect_model_assignment_divergence(
        repo_root=FIXTURES / "detector-3-negative",
        audit_log_path=FIXTURES / "detector-3-negative" / "audit-log.jsonl",
    )
    assert findings == []


def test_detector_3_boundary_no_audit_log(rl):
    """No audit log → empty findings, not error."""
    findings = rl.detect_model_assignment_divergence(
        repo_root=FIXTURES / "detector-3-boundary",
        audit_log_path=None,
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Detector #4 — enforcement_commit_unpopulated
# ---------------------------------------------------------------------------

def test_detector_4_positive_fixture(rl):
    findings = rl.detect_enforcement_commit_unpopulated(
        repo_root=FIXTURES / "detector-4-positive",
    )
    assert len(findings) == 1
    assert "ADR-999" in findings[0]["_extra"]["adr"]


def test_detector_4_negative_fixture(rl):
    findings = rl.detect_enforcement_commit_unpopulated(
        repo_root=FIXTURES / "detector-4-negative",
    )
    assert findings == []


def test_detector_4_boundary_superseded_skipped(rl):
    """SUPERSEDED ADRs must not fire detector #4."""
    findings = rl.detect_enforcement_commit_unpopulated(
        repo_root=FIXTURES / "detector-4-boundary",
    )
    assert findings == []


def test_detector_4_reproduces_adr_067_ground_truth(rl):
    """Acceptance: ADR-067 enforcement_commit unpopulated at HEAD."""
    findings = rl.detect_enforcement_commit_unpopulated(repo_root=REPO_ROOT)
    adrs = {f["_extra"]["adr"] for f in findings}
    assert "ADR-067-ceo-model-downshift-static-routing.md" in adrs, (
        "ADR-067 ground truth: §4.3 acceptance row 4 — enforcement_commit "
        "unpopulated. If this regresses, fixture must be updated."
    )


# ---------------------------------------------------------------------------
# Detector #6 — audit_action_phantom
# ---------------------------------------------------------------------------

def test_detector_6_positive_fixture(rl):
    findings = rl.detect_audit_action_phantom(
        repo_root=FIXTURES / "detector-6-positive",
    )
    actions = {f["_extra"]["action"] for f in findings}
    assert "fixture_phantom_action_xyz" in actions


def test_detector_6_negative_fixture(rl):
    findings = rl.detect_audit_action_phantom(
        repo_root=FIXTURES / "detector-6-negative",
    )
    # 'agent_spawn' IS in fixture _KNOWN_ACTIONS — no phantom
    assert findings == []


def test_detector_6_boundary_dynamic_action_not_flagged(rl):
    """Dynamic (non-literal) action arg must not be phantom-flagged."""
    findings = rl.detect_audit_action_phantom(
        repo_root=FIXTURES / "detector-6-boundary",
    )
    assert findings == []


def test_detector_6_reproduces_skill_bootstrap_used_precedent(rl):
    """Acceptance: skill_bootstrap_used IS registered post-Codex-S76; no phantom.

    Pre-Codex-S76 (Session 76) `skill_bootstrap_used` was emitted in
    check_skill_patch_sentinel.py:251 but missing from `_KNOWN_ACTIONS`.
    Post-fix it's registered (audit_emit.py:216). Detector #6 must NOT
    flag it at HEAD; the test exists to lock-in the precedent shape.
    """
    findings = rl.detect_audit_action_phantom(repo_root=REPO_ROOT)
    actions = {f["_extra"]["action"] for f in findings}
    assert "skill_bootstrap_used" not in actions


def test_detector_6_no_phantoms_at_head(rl):
    """Belt-and-suspenders: HEAD audit_emit.py + emitter scan = 0 phantoms."""
    findings = rl.detect_audit_action_phantom(repo_root=REPO_ROOT)
    # Snapshot: at HEAD this should be 0; if non-zero, something drifted.
    assert findings == [], (
        f"Phantom action(s) detected at HEAD: "
        f"{[f['_extra']['action'] for f in findings]}"
    )


# ---------------------------------------------------------------------------
# Self-exclusion tests
# ---------------------------------------------------------------------------

def test_self_exclusion_task_route_skipped(rl, tmp_path):
    """task-route.py mention of an env var must NOT be counted as a read."""
    # task-route.py at HEAD doesn't currently read CEO_MODEL_DOWNSHIFT, but
    # even if it did (hypothetically), the AST scan must skip it via
    # SELF_EXCLUDE_BASENAMES. Verify by checking _is_excluded directly.
    p = REPO_ROOT / ".claude" / "scripts" / "task-route.py"
    assert rl._is_excluded(p, repo_root=REPO_ROOT)


def test_self_exclusion_reality_ledger_skipped(rl):
    p = REPO_ROOT / ".claude" / "scripts" / "reality-ledger.py"
    assert rl._is_excluded(p, repo_root=REPO_ROOT)


def test_self_exclusion_owner_ceremony_archive(rl, tmp_path):
    """Files under owner-ceremony/archive/** must be excluded."""
    fake = tmp_path / "owner-ceremony" / "archive" / "old-script.py"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text("# noop", encoding="utf-8")
    assert rl._is_excluded(fake, repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Output rendering contract — claim_source_path inclusion/exclusion
# ---------------------------------------------------------------------------

def test_render_markdown_includes_claim_source_path(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:42",
        expected_evidence="x",
        actual_evidence="y",
        advisory_action="z",
    )
    md = rl.render_finding_markdown(f)
    assert "docs/X.md:42" in md
    assert "claim_source_path" in md


def test_render_json_excludes_claim_source_path(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:42",
        expected_evidence="x",
        actual_evidence="y",
        advisory_action="z",
    )
    out = rl.render_findings_json([f])
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert "claim_source_path" not in parsed[0]
    assert "claim_source_sha256" in parsed[0]
    assert parsed[0]["claim_source_sha256"]


def test_render_jsonl_excludes_claim_source_path(rl):
    f = rl._build_finding(
        detector="enforcement_commit_unpopulated",
        severity="low",
        confidence=0.97,
        claim_source_path=".claude/adr/ADR-067-x.md:169",
        expected_evidence="x",
        actual_evidence="y",
        advisory_action="z",
    )
    out = rl.render_findings_jsonl([f])
    line = out.strip().splitlines()[0]
    parsed = json.loads(line)
    assert "claim_source_path" not in parsed
    assert "claim_source_sha256" in parsed


def test_render_json_excludes_extra_debug_field(rl):
    """_extra is private debug payload; must not leak to JSON."""
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence="y",
        advisory_action="z",
        extra={"secret_debug": "HIDE_ME"},
    )
    out = rl.render_findings_json([f])
    assert "HIDE_ME" not in out
    assert "_extra" not in out


def test_render_markdown_zero_findings(rl):
    out = rl.render_findings_markdown([])
    assert "0 findings" in out


# ---------------------------------------------------------------------------
# Redaction tests (≥10)
# ---------------------------------------------------------------------------

SK_CRED = "sk-test-AAAAAAAAAAAAAAAAAAAA"


def test_redact_sk_credential_replaced(rl):
    out = rl._redact(f"some text with {SK_CRED} embedded")
    assert SK_CRED not in out
    assert "[API_KEY]" in out


def test_redact_idempotent(rl):
    once = rl._redact(f"key={SK_CRED}")
    twice = rl._redact(once)
    assert once == twice


def test_redact_handles_none(rl):
    assert rl._redact(None) == ""


def test_redact_empty_string(rl):
    assert rl._redact("") == ""


def test_finding_actual_evidence_is_redacted(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence=f"raw evidence containing {SK_CRED}",
        advisory_action="z",
    )
    assert SK_CRED not in f["actual_evidence_redacted"]
    assert "[API_KEY]" in f["actual_evidence_redacted"]


def test_finding_actual_evidence_redacted_in_markdown(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence=f"see {SK_CRED}",
        advisory_action="z",
    )
    md = rl.render_finding_markdown(f)
    assert SK_CRED not in md
    assert "[API_KEY]" in md


def test_finding_actual_evidence_redacted_in_json(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence=f"json {SK_CRED}",
        advisory_action="z",
    )
    out = rl.render_findings_json([f])
    assert SK_CRED not in out


def test_finding_actual_evidence_redacted_in_jsonl(rl):
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence=f"jsonl {SK_CRED}",
        advisory_action="z",
    )
    out = rl.render_findings_jsonl([f])
    assert SK_CRED not in out


def test_redact_corpus_fixture(rl):
    """Detector swept over the redaction fixture corpus produces no plaintext."""
    corpus = (FIXTURES / "redaction" / "_test_corpus.py").read_text(encoding="utf-8")
    redacted = rl._redact(corpus)
    assert SK_CRED not in redacted


def test_sha256_of_path_consistent(rl):
    a = rl._sha256_of("docs/X.md:42")
    b = rl._sha256_of("docs/X.md:42")
    assert a == b
    assert len(a) == 64


# ---------------------------------------------------------------------------
# Audit emission allowlist + scrub
# ---------------------------------------------------------------------------

def test_scrub_drops_disallowed_keys(rl):
    payload = {
        "action": "reality_ledger_finding",
        "ts": "2026-05-05T00:00:00Z",
        "detector": "runtime_read_missing",
        "severity": "medium",
        # confidence_bps: int 0..1000 (replaces float "confidence").
        "confidence_bps": 950,
        "claim_source_sha256": "deadbeef",
        "finding_count_in_run": 3,
        # disallowed:
        "claim_source_path": "docs/X.md:42",
        "actual_evidence_redacted": "stuff",
        "expected_evidence": "stuff",
    }
    kept, dropped = rl._scrub_reality_ledger_event(payload)
    assert "claim_source_path" not in kept
    assert "actual_evidence_redacted" not in kept
    assert "expected_evidence" not in kept
    assert "claim_source_path" in dropped
    assert "actual_evidence_redacted" in dropped
    # Old float field "confidence" is not in allowlist (will be dropped).
    old_float_payload = dict(payload)
    old_float_payload["confidence"] = 0.95
    kept2, dropped2 = rl._scrub_reality_ledger_event(old_float_payload)
    assert "confidence" in dropped2, "old float field must be excluded by allowlist"


def test_scrub_keeps_allowlist_only(rl):
    payload = {k: "x" for k in rl._REALITY_LEDGER_FINDING_ALLOWLIST}
    payload["forbidden"] = "leak"
    kept, dropped = rl._scrub_reality_ledger_event(payload)
    assert set(kept.keys()) == set(rl._REALITY_LEDGER_FINDING_ALLOWLIST)
    assert "forbidden" in dropped


def test_try_emit_finding_never_raises(rl):
    """Unwired audit_emit action must not raise — advisory-only fallback."""
    f = rl._build_finding(
        detector="runtime_read_missing",
        severity="medium",
        confidence=0.9,
        claim_source_path="docs/X.md:1",
        expected_evidence="x",
        actual_evidence="y",
        advisory_action="z",
    )
    # Should not raise even if 'reality_ledger_finding' is not yet registered
    rl._try_emit_finding(f, finding_count_in_run=1)


# ---------------------------------------------------------------------------
# Severity filtering
# ---------------------------------------------------------------------------

def test_filter_by_severity_low_passes_all(rl):
    findings = [
        {"severity": "low"},
        {"severity": "medium"},
        {"severity": "high"},
    ]
    assert len(rl.filter_by_severity(findings, "low")) == 3


def test_filter_by_severity_medium(rl):
    findings = [
        {"severity": "low"},
        {"severity": "medium"},
        {"severity": "high"},
    ]
    out = rl.filter_by_severity(findings, "medium")
    severities = sorted(f["severity"] for f in out)
    assert severities == ["high", "medium"]


def test_filter_by_severity_high_only(rl):
    findings = [
        {"severity": "low"},
        {"severity": "high"},
    ]
    out = rl.filter_by_severity(findings, "high")
    assert len(out) == 1
    assert out[0]["severity"] == "high"


# ---------------------------------------------------------------------------
# Run dispatch + timeout
# ---------------------------------------------------------------------------

def test_run_detectors_default_runs_all(rl):
    findings, errors = rl.run_detectors(repo_root=REPO_ROOT)
    assert errors == [] or all("timed out" not in e for e in errors)
    # At least the ADR-067 ground truth + requirements.lock placeholder
    assert len(findings) >= 2
    detectors = {f["detector"] for f in findings}
    assert "enforcement_commit_unpopulated" in detectors
    assert "installable_claim_drift" in detectors


def test_run_detectors_single_detector(rl):
    findings, errors = rl.run_detectors(
        repo_root=REPO_ROOT,
        detector_names=["installable_claim_drift"],
    )
    assert errors == []
    detectors = {f["detector"] for f in findings}
    assert detectors == {"installable_claim_drift"}


def test_run_detectors_unknown_detector_records_error(rl):
    findings, errors = rl.run_detectors(
        repo_root=REPO_ROOT,
        detector_names=["nonexistent_detector"],
    )
    assert any("unknown detector" in e for e in errors)
    assert findings == []


def test_run_detectors_timeout_does_not_raise(rl):
    """1ms timeout must result in advisory error, not exception."""
    findings, errors = rl.run_detectors(
        repo_root=REPO_ROOT,
        detector_names=["runtime_read_missing"],
        timeout_ms=1,
    )
    # Either it completed in <1ms (impossible at repo scale) or it hit the
    # ITIMER guard. Acceptable if errors are present OR findings empty.
    assert isinstance(findings, list)
    assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# CLI exit-code contract
# ---------------------------------------------------------------------------

def _run_cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_exit_zero_on_success_with_findings():
    res = _run_cli("--detector", "installable_claim_drift", "--format", "markdown")
    assert res.returncode == 0
    assert "installable_claim_drift" in res.stdout


def test_cli_exit_zero_on_zero_findings():
    """Detector #6 currently produces 0 phantoms at HEAD; exit must be 0."""
    res = _run_cli("--detector", "audit_action_phantom", "--format", "markdown")
    assert res.returncode == 0


def test_cli_invalid_repo_root_exits_2(tmp_path):
    res = _run_cli("--repo-root", str(tmp_path / "nonexistent_dir_xyz"))
    assert res.returncode == 2


def test_cli_format_json_no_path_field():
    res = _run_cli("--detector", "installable_claim_drift", "--format", "json")
    assert res.returncode == 0
    parsed = json.loads(res.stdout)
    if parsed:
        for f in parsed:
            assert "claim_source_path" not in f
            assert "claim_source_sha256" in f


def test_cli_format_jsonl_no_path_field():
    res = _run_cli("--detector", "installable_claim_drift", "--format", "jsonl")
    assert res.returncode == 0
    for line in res.stdout.strip().splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        assert "claim_source_path" not in parsed


def test_cli_severity_filter_high_excludes_low():
    res = _run_cli("--severity", "high", "--format", "json")
    assert res.returncode == 0
    parsed = json.loads(res.stdout)
    for f in parsed:
        assert f["severity"] == "high"


def test_cli_output_to_file(tmp_path):
    out = tmp_path / "report.md"
    res = _run_cli(
        "--detector", "installable_claim_drift",
        "--format", "markdown",
        "--output", str(out),
    )
    assert res.returncode == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "installable_claim_drift" in text


# ---------------------------------------------------------------------------
# Issue body template fixture contract
# ---------------------------------------------------------------------------

def test_issue_body_template_exists():
    p = FIXTURES / "issue-body-template.md"
    assert p.exists()


def test_issue_body_template_excludes_claim_source_path():
    """Phase 4 R-SEC NTH #4: issue body must never embed claim_source_path."""
    p = FIXTURES / "issue-body-template.md"
    text = p.read_text(encoding="utf-8")
    # Template MUST NOT have a line of the form `claim_source_path:` (only sha)
    # The template MAY mention the field name in a sentence forbidding it.
    # Assert the rule that rendered findings have no path key:
    assert "claim_source_sha256" in text
    assert "never** included" in text or "is **never**" in text


# =============================================================================
# PLAN-078 Wave 2 — Detector #7 estimate-drift tests.
# =============================================================================

import contextlib  # noqa: E402


@contextlib.contextmanager
def _planned_repo(tmp_path, plan_files):
    """Build a tmp repo with `.claude/plans/` populated.

    `plan_files` is a dict: filename -> file content (string).
    """
    repo = tmp_path / "repo"
    plans = repo / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    for name, content in plan_files.items():
        (plans / name).write_text(content, encoding="utf-8")
    yield repo


def test_detect_07_disabled_via_env(rl, tmp_path, monkeypatch):
    """Bypass: CEO_REALITY_LEDGER_DETECTOR_07=0 → empty findings."""
    monkeypatch.setenv("CEO_REALITY_LEDGER_DETECTOR_07", "0")
    with _planned_repo(tmp_path, {
        "PLAN-001-foo.md": (
            "---\nid: PLAN-001\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={"plans/PLAN-001-foo.md": []},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert out == []


def test_detect_07_skip_when_no_plans_dir(rl, tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    out = rl.detect_estimate_drift(
        repo_root=repo,
        git_log_index={},
        calibration_csv=tmp_path / "calib.csv",
    )
    assert out == []


def test_detect_07_skip_plan_without_estimate(rl, tmp_path):
    with _planned_repo(tmp_path, {
        "PLAN-005-no-est.md": (
            "---\nid: PLAN-005\nstatus: done\ncreated: 2026-04-05\n---\n\n# body\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-005-no-est.md": [
                ("a" * 40, "2026-04-05T10:00:00+00:00", False),
                ("b" * 40, "2026-04-06T10:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert out == []


def test_detect_07_skip_plan_status_not_done(rl, tmp_path):
    with _planned_repo(tmp_path, {
        "PLAN-002-draft.md": (
            "---\nid: PLAN-002\nstatus: executing\n"
            "estimate:\n  compute_hours: 4-6\n  owner_physical_min: 10\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-002-draft.md": []},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert out == []


def test_detect_07_emits_finding_on_drift(rl, tmp_path):
    """Plan estimated 1-2h but actual span 50h → high severity."""
    with _planned_repo(tmp_path, {
        "PLAN-100-drift.md": (
            "---\nid: PLAN-100\nstatus: done\ncreated: 2026-04-10\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        # 50-hour span, 0 GPG signatures
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-100-drift.md": [
                ("a" * 40, "2026-04-10T10:00:00+00:00", False),
                ("b" * 40, "2026-04-12T12:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    assert out[0]["detector"] == "estimate_drift"
    assert out[0]["severity"] == "high"  # 50h / 1.5h = 33× → high
    assert out[0]["_extra"]["compute_drift_factor"] > 10.0


def test_detect_07_skip_when_no_drift(rl, tmp_path):
    """Estimate 50-60h, actual 55h → no finding."""
    with _planned_repo(tmp_path, {
        "PLAN-200-onspec.md": (
            "---\nid: PLAN-200\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 50-60\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-200-onspec.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-03T15:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    # 55h span vs 50-60h estimate → factor 1.0 → below 1.2 threshold → no finding
    assert out == []


def test_detect_07_uses_created_field(rl, tmp_path):
    """Per Codex CDX-UNIQUE-06: `created` is canonical, NOT `created_at`."""
    with _planned_repo(tmp_path, {
        "PLAN-300-created.md": (
            "---\nid: PLAN-300\nstatus: done\ncreated: 2026-04-15\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-300-created.md": [
                ("a" * 40, "2026-04-15T08:00:00+00:00", False),
                ("b" * 40, "2026-04-16T08:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    if out:  # may have drift finding
        assert out[0]["_extra"]["created_field"] == "2026-04-15"


def test_detect_07_falls_back_to_created_at(rl, tmp_path):
    """When `created` absent, detector falls back to `created_at`."""
    with _planned_repo(tmp_path, {
        "PLAN-301-createdat.md": (
            "---\nid: PLAN-301\nstatus: done\ncreated_at: 2026-04-20\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-301-createdat.md": [
                ("a" * 40, "2026-04-20T08:00:00+00:00", False),
                ("b" * 40, "2026-04-23T08:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    if out:
        assert out[0]["_extra"]["created_field"] == "2026-04-20"


def test_detect_07_severity_bands(rl):
    """severity bands — bidirectional ratio max(f, 1/f).

    Codex W1+W2 fix-pack #3 (Fix #3): detector now flags both overruns
    (factor > 1.2) and underruns (factor < 0.83 ≈ 1/1.2). Severity
    classification uses the symmetric ratio:

      ≤ 1.2 → low (no drift; threshold filter skips finding)
      1.2 < r ≤ 1.5 → low
      1.5 < r ≤ 2.0 → medium
      r > 2.0 → high
    """
    # No-drift band (r ≤ 1.2)
    assert rl._drift_severity(1.0, 1.0) == "low"
    assert rl._drift_severity(1.1, 1.0) == "low"
    # Overrun side
    assert rl._drift_severity(1.4, 1.0) == "low"  # 1.4 ≤ 1.5 → low
    assert rl._drift_severity(1.6, 1.0) == "medium"  # 1.5 < 1.6 ≤ 2.0
    assert rl._drift_severity(1.99, 1.0) == "medium"
    assert rl._drift_severity(2.5, 1.0) == "high"
    # Underrun side (Codex Fix #3 — bidirectional)
    assert rl._drift_severity(0.5, 1.0) == "medium"  # 1/0.5 = 2.0 → medium
    assert rl._drift_severity(0.3, 1.0) == "high"  # 1/0.3 ≈ 3.33 → high
    assert rl._drift_severity(0.83, 1.0) == "low"  # 1/0.83 ≈ 1.205 ≤ 1.5


def test_detect_07_classify_bias(rl):
    assert rl._classify_bias(actual_compute=10, est_compute_lo=1, est_compute_hi=2) == "underestimate"
    assert rl._classify_bias(actual_compute=0.5, est_compute_lo=1, est_compute_hi=2) == "overestimate"
    assert rl._classify_bias(actual_compute=1.5, est_compute_lo=1, est_compute_hi=2) == ""


def test_detect_07_parse_estimate_block(rl):
    """Verify `_parse_estimate_block` handles compute_hours / owner_physical_min."""
    text = (
        "---\nid: PLAN-X\nstatus: done\nestimate:\n"
        "  compute_hours: 5-10  # advisory\n"
        "  owner_physical_min: 30\n"
        "  calendar_buffer_days: 0\n"
        "owner: CEO\n---\n"
    )
    out = rl._parse_estimate_block(text)
    assert out.get("compute_hours") == "5-10"
    assert out.get("owner_physical_min") == "30"
    assert out.get("calendar_buffer_days") == "0"


def test_detect_07_coerce_hours_pair(rl):
    assert rl._coerce_hours_to_pair("5-10") == (5.0, 10.0)
    assert rl._coerce_hours_to_pair("8") == (8.0, 8.0)
    assert rl._coerce_hours_to_pair("12-8") == (8.0, 12.0)  # auto-swap
    assert rl._coerce_hours_to_pair("") is None
    assert rl._coerce_hours_to_pair("not a number") is None


def test_detect_07_csv_idempotent(rl, tmp_path):
    """Codex W1+W2 fix-pack #4: dedup excludes run_iso8601 column."""
    csv = tmp_path / "out.csv"
    # Row A and exact-duplicate
    rl._append_calibration_csv(csv, "PLAN-X,2026-04-01T00:00:00Z,1,2,3,5,10,1.5,2.0,medium,underestimate")
    rl._append_calibration_csv(csv, "PLAN-X,2026-04-01T00:00:00Z,1,2,3,5,10,1.5,2.0,medium,underestimate")
    # Different plan
    rl._append_calibration_csv(csv, "PLAN-Y,2026-04-02T00:00:00Z,5,10,8,5,15,1.0,3.0,high,underestimate")
    rows = csv.read_text().splitlines()
    # 1 header + 2 unique rows
    assert len(rows) == 3
    assert rows[0].startswith("plan_id,run_iso8601,")
    assert "PLAN-X" in rows[1]
    assert "PLAN-Y" in rows[2]


def test_detect_07_csv_dedup_ignores_run_iso(rl, tmp_path):
    """Codex W1+W2 fix-pack #4 acceptance: same plan + same drift signature
    across DIFFERENT run_iso8601 timestamps still dedups to 1 data row.

    Prior dedup compared the ENTIRE row including the per-run timestamp,
    so reruns always produced N rows after N runs (CSV grew unbounded).
    """
    csv = tmp_path / "out.csv"
    rl._append_calibration_csv(
        csv,
        "PLAN-X,2026-04-01T00:00:00Z,1,2,3,5,10,1.5,2.0,medium,underestimate",
    )
    # Same plan, same drift signature, FRESH run_iso8601 — must dedup.
    rl._append_calibration_csv(
        csv,
        "PLAN-X,2026-04-08T15:30:00Z,1,2,3,5,10,1.5,2.0,medium,underestimate",
    )
    # And again with another fresh timestamp
    rl._append_calibration_csv(
        csv,
        "PLAN-X,2026-05-01T09:00:00Z,1,2,3,5,10,1.5,2.0,medium,underestimate",
    )
    rows = csv.read_text().splitlines()
    # 1 header + 1 dedup'd data row across 3 runs
    assert len(rows) == 2, (
        f"expected exactly 1 data row across 3 runs (dedup excludes "
        f"run_iso8601); got {len(rows)} lines: {rows}"
    )
    assert rows[0].startswith("plan_id,run_iso8601,")
    assert rows[1].startswith("PLAN-X,")


def test_detect_07_csv_header_first(rl, tmp_path):
    csv = tmp_path / "fresh.csv"
    rl._append_calibration_csv(csv, "PLAN-Z,2026-04-01T00:00:00Z,1,2,3,5,10,1.5,1.0,low,")
    rows = csv.read_text().splitlines()
    assert rows[0].startswith("plan_id,run_iso8601,")
    assert rows[1].startswith("PLAN-Z,")


def test_detect_07_manual_owner_override(rl, tmp_path):
    with _planned_repo(tmp_path, {
        "PLAN-400-manual.md": (
            "---\nid: PLAN-400\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n"
            "actual_owner_physical_min: 60\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-400-manual.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-04T08:00:00+00:00", True),  # GPG signed
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    # Manual override 60 used, NOT 5min*1gpg=5min
    assert out[0]["_extra"]["actual_owner_min_estimated"] == 60.0


def test_detect_07_manual_owner_clamp(rl, tmp_path):
    """Manual override clamped to 0..10000."""
    with _planned_repo(tmp_path, {
        "PLAN-401-clamp.md": (
            "---\nid: PLAN-401\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n"
            "actual_owner_physical_min: 999999\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-401-clamp.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-08T08:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    assert out[0]["_extra"]["actual_owner_min_estimated"] == 10000.0  # clamped


def test_detect_07_gpg_signed_count_mapping(rl, tmp_path):
    """GPG-signed count drives default owner_min when no manual override."""
    with _planned_repo(tmp_path, {
        "PLAN-500-gpg.md": (
            "---\nid: PLAN-500\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-500-gpg.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", True),  # signed
                ("b" * 40, "2026-04-02T08:00:00+00:00", True),  # signed
                ("c" * 40, "2026-04-03T08:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    # 2 GPG signatures → 2 * 5min = 10min
    assert out[0]["_extra"]["gpg_signed_commits"] == 2
    assert out[0]["_extra"]["actual_owner_min_estimated"] == 10.0


def test_detect_07_skip_no_git_evidence(rl, tmp_path):
    """When git_log_index has no entries for plan, detector skips silently."""
    with _planned_repo(tmp_path, {
        "PLAN-600-nogit.md": (
            "---\nid: PLAN-600\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert out == []


def test_detect_07_systematic_bias_underestimate(rl, tmp_path):
    """N=5+ same-direction medium+ findings → recommendation event appended."""
    plan_files = {}
    git_index = {}
    for i in range(6):
        slug = f"PLAN-{700 + i}-bias.md"
        plan_files[slug] = (
            f"---\nid: PLAN-{700 + i}\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        )
        git_index[f".claude/plans/{slug}"] = [
            ("a" * 40 + str(i), "2026-04-01T00:00:00+00:00", False),
            ("b" * 40 + str(i), "2026-04-05T00:00:00+00:00", False),
        ]
    with _planned_repo(tmp_path, plan_files) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=tmp_path / "calib.csv",
        )
    # 6 plans + 1 recommendation = 7
    assert len(out) >= 6
    rec = [f for f in out if f["_extra"].get("is_recommendation_event")]
    assert len(rec) == 1
    assert rec[0]["_extra"]["systematic_bias_direction"] == "underestimate"
    assert rec[0]["_extra"]["plans_affected_count"] >= 5
    assert rec[0]["severity"] == "high"


def test_detect_07_no_systematic_bias_below_threshold(rl, tmp_path):
    """N<5 → no recommendation event."""
    plan_files = {}
    git_index = {}
    for i in range(3):
        slug = f"PLAN-{800 + i}-below.md"
        plan_files[slug] = (
            f"---\nid: PLAN-{800 + i}\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        )
        git_index[f".claude/plans/{slug}"] = [
            ("a" * 40 + str(i), "2026-04-01T00:00:00+00:00", False),
            ("b" * 40 + str(i), "2026-04-05T00:00:00+00:00", False),
        ]
    with _planned_repo(tmp_path, plan_files) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=tmp_path / "calib.csv",
        )
    rec = [f for f in out if f["_extra"].get("is_recommendation_event")]
    assert rec == []


def test_detect_07_idempotent_repeat_run(rl, tmp_path):
    """Codex W1+W2 fix-pack #4 acceptance: CSV row count is 1 across reruns.

    Prior behavior: each rerun produced a fresh ``run_iso8601`` so the
    "exact match" dedup never fired; CSV grew unbounded.
    Post-Fix #4: dedup key excludes ``run_iso8601`` → repeat runs of the
    same plan with the same drift signature produce exactly 1 data row.
    """
    csv = tmp_path / "calib.csv"
    plan_files = {
        "PLAN-900-idem.md": (
            "---\nid: PLAN-900\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }
    git_index = {".claude/plans/PLAN-900-idem.md": [
        ("a" * 40, "2026-04-01T00:00:00+00:00", False),
        ("b" * 40, "2026-04-04T00:00:00+00:00", False),
    ]}
    with _planned_repo(tmp_path, plan_files) as repo:
        out1 = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=csv,
        )
    with _planned_repo(tmp_path, plan_files) as repo:
        out2 = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=csv,
        )
    # Codex S89 Fix #4 strengthening: 3 reruns (not 2) per spec — verifies
    # dedup is stable across multiple invocations, not just one repeat.
    with _planned_repo(tmp_path, plan_files) as repo:
        out3 = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=csv,
        )
    # Same finding count across all 3 runs
    assert len(out1) == len(out2) == len(out3)
    # Codex Fix #4 strict acceptance: CSV did NOT duplicate across 3 reruns.
    rows = csv.read_text().splitlines()
    # Header + exactly 1 data row (out1 produced 1 row; out2+out3 must dedup)
    data_rows = [r for r in rows[1:] if r.strip()]
    assert len(data_rows) == 1, (
        f"CSV duplicated across 3 reruns (Codex Fix #4 regression). "
        f"Expected 1 data row; got {len(data_rows)}: {data_rows}"
    )


def test_detect_07_registered_in_dispatch(rl, tmp_path):
    """run_detectors must include estimate_drift in its dispatch table."""
    repo = tmp_path / "r"
    (repo / ".claude" / "plans").mkdir(parents=True)
    findings, errors = rl.run_detectors(
        repo_root=repo, detector_names=["estimate_drift"]
    )
    # Empty plans dir → 0 findings, 0 errors
    assert findings == []
    assert errors == []


def test_detect_07_in_detector_registry(rl):
    """estimate_drift entry present in DETECTOR_REGISTRY."""
    assert "estimate_drift" in rl.DETECTOR_REGISTRY
    assert rl.DETECTOR_REGISTRY["estimate_drift"]["severity"] == "medium"


def test_detect_07_severity_finding_overrides_registry_default(rl, tmp_path):
    """Finding severity is computed per-call (not always 'medium' default)."""
    with _planned_repo(tmp_path, {
        "PLAN-110-low.md": (
            "---\nid: PLAN-110\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 10-15\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-110-low.md": [
                ("a" * 40, "2026-04-01T00:00:00+00:00", False),
                # 18h span vs 10-15h estimate → ratio = 18/12.5 = 1.44× → low
                ("b" * 40, "2026-04-01T18:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    if out:
        assert out[0]["severity"] == "low"


def test_detect_07_invalid_manual_override_falls_open(rl, tmp_path):
    """`actual_owner_physical_min: not-a-number` → falls back to GPG count."""
    with _planned_repo(tmp_path, {
        "PLAN-120-invalid.md": (
            "---\nid: PLAN-120\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n"
            "actual_owner_physical_min: not_a_number\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-120-invalid.md": [
                ("a" * 40, "2026-04-01T00:00:00+00:00", True),  # 1 GPG
                ("b" * 40, "2026-04-04T00:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    # Falls back to GPG count: 1 * 5 = 5
    assert out[0]["_extra"]["actual_owner_min_estimated"] == 5.0


def test_detect_07_csv_columns_complete(rl, tmp_path):
    csv = tmp_path / "full.csv"
    with _planned_repo(tmp_path, {
        "PLAN-130-csv.md": (
            "---\nid: PLAN-130\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5-10\n---\n"
        ),
    }) as repo:
        rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-130-csv.md": [
                ("a" * 40, "2026-04-01T00:00:00+00:00", False),
                ("b" * 40, "2026-04-04T00:00:00+00:00", False),
            ]},
            calibration_csv=csv,
        )
    rows = csv.read_text().splitlines()
    assert len(rows) >= 2
    # Header has 11 columns; data row should match
    header_cols = rows[0].split(",")
    data_cols = rows[1].split(",")
    assert len(header_cols) == 11
    assert len(data_cols) == 11
    assert "PLAN-130" in data_cols[0]


def test_detect_07_handles_negative_drift(rl, tmp_path):
    """Codex W1+W2 fix-pack #3: 50-60h estimated, 5h actual = HIGH-severity underrun.

    Prior behavior (PRE-Fix #3): detector only flagged overruns
    (max(|f|, 1/|f|) collapsed to max(|f|, 1.0)); a massive overestimate
    silently passed. Codex Phase 1.D found this gap: per spec, both
    sides of estimate-drift are equally diagnostic, and the test here
    explicitly expected NO finding for an extreme overestimate.

    Post-Fix #3: bidirectional. drift factor = 5/55 ≈ 0.091; symmetric
    ratio = 1/0.091 ≈ 11× → high. bias_direction = "overestimate"
    (actual fell BELOW estimate range).
    """
    with _planned_repo(tmp_path, {
        "PLAN-140-over.md": (
            "---\nid: PLAN-140\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 50-60\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-140-over.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-01T13:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    # Created 2026-04-01T00:00 UTC → closeout 2026-04-01T13:00 = 13h span;
    # estimate mid = 55h → factor = 13/55 ≈ 0.236 → underrun.
    # Symmetric ratio ≈ 1/0.236 = 4.24 → HIGH severity.
    assert isinstance(out, list)
    assert len(out) == 1, f"expected 1 underrun finding, got {len(out)}: {out}"
    assert out[0]["detector"] == "estimate_drift"
    assert out[0]["severity"] == "high", (
        f"expected HIGH-severity underrun; got {out[0]['severity']}. "
        f"_extra={out[0].get('_extra')}"
    )
    # bias_direction documents direction of estimate error
    assert out[0]["_extra"]["bias_direction"] == "overestimate"
    # Drift factor < 0.83 confirms underrun side
    assert out[0]["_extra"]["compute_drift_factor"] < 0.83


def test_detect_07_plan_file_id_extraction(rl, tmp_path):
    """`PLAN-901-foo.md` → plan_id `PLAN-901`."""
    with _planned_repo(tmp_path, {
        "PLAN-901-myplan.md": (
            "---\nid: PLAN-901\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-901-myplan.md": [
                ("a" * 40, "2026-04-01T00:00:00+00:00", False),
                ("b" * 40, "2026-04-05T00:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    assert any(f["_extra"]["plan_id"] == "PLAN-901" for f in out)


def test_detect_07_zero_division_guards(rl):
    """Edge: estimate range (0,0) → no zero-div crash."""
    pair = rl._coerce_hours_to_pair("0-0")
    assert pair == (0.0, 0.0)


def test_detect_07_invocation_via_run_detectors(rl, tmp_path):
    """The detector is dispatched correctly from run_detectors."""
    with _planned_repo(tmp_path, {
        "PLAN-900-via-run.md": (
            "---\nid: PLAN-900\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        # run_detectors uses real git which won't find this file in the new
        # repo dir; we still verify it doesn't crash + returns proper shape.
        findings, errors = rl.run_detectors(
            repo_root=repo, detector_names=["estimate_drift"]
        )
    # No git history → no findings, no errors
    assert errors == []
    assert isinstance(findings, list)


def test_detect_07_extract_top_level_field_strips_comments(rl):
    """`status: done  # comment` → `done`."""
    text = "---\nstatus: done  # ok\nid: PLAN-X\n---\n"
    assert rl._extract_top_level_field(text, "status") == "done"
    assert rl._extract_top_level_field(text, "id") == "PLAN-X"
    assert rl._extract_top_level_field(text, "missing") is None


def test_detect_07_extract_top_level_field_strips_quotes(rl):
    text = "---\nfoo: \"bar\"\nbaz: 'qux'\n---\n"
    assert rl._extract_top_level_field(text, "foo") == "bar"
    assert rl._extract_top_level_field(text, "baz") == "qux"


def test_detect_07_audit_emit_action_registered_in_staged():
    """Wave 2 staged audit_emit must register `estimate_drift_detected`."""
    import importlib.util as _ilu
    staged = REPO_ROOT / ".claude" / "plans" / "PLAN-078" / "staging" / "wave-1" / "audit_emit.py"
    if not staged.is_file():
        pytest.skip("staged audit_emit.py not present")
    spec = _ilu.spec_from_file_location("staged_ae_w2", staged)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "estimate_drift_detected" in mod._KNOWN_ACTIONS
    assert "estimate_drift_systematic_bias" in mod._KNOWN_ACTIONS
    assert hasattr(mod, "emit_estimate_drift_detected")
    assert hasattr(mod, "emit_estimate_drift_systematic_bias")


def test_detect_07_allowlist_contract():
    """Wave 2 allowlist matches the plan §4 Wave 2 6-field contract.

    Codex W1+W2 fix-pack #2: drift_factor_* renamed to *_basis_points
    (int) — canonical_json forbids floats in HMAC-covered fields.
    """
    import importlib.util as _ilu
    staged = REPO_ROOT / ".claude" / "plans" / "PLAN-078" / "staging" / "wave-1" / "audit_emit.py"
    if not staged.is_file():
        pytest.skip("staged audit_emit.py not present")
    spec = _ilu.spec_from_file_location("staged_ae_w2b", staged)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    contract_fields = {
        "plan_id",
        "drift_factor_compute_basis_points",
        "drift_factor_owner_basis_points",
        "severity", "plan_count_in_run", "systematic_bias_direction",
    }
    assert contract_fields <= set(mod._ESTIMATE_DRIFT_DETECTED_ALLOWLIST)


# ===========================================================================
# Codex W1+W2 fix-pack — Fix #1 (typed audit emit wiring)
# ===========================================================================


class _StubAuditEmit:
    """Recording stub that mirrors the typed audit_emit interface for tests."""

    def __init__(self):
        self.detected_calls = []
        self.systematic_bias_calls = []
        self.generic_calls = []

    def emit_estimate_drift_detected(self, **kwargs):
        self.detected_calls.append(kwargs)

    def emit_estimate_drift_systematic_bias(self, **kwargs):
        self.systematic_bias_calls.append(kwargs)

    def emit_generic(self, action, **kwargs):
        self.generic_calls.append((action, kwargs))


def test_detect_07_emits_via_typed_emitter_not_generic(rl, tmp_path):
    """Codex W1+W2 fix-pack #1: detector #7 calls emit_estimate_drift_detected,
    NOT generic _try_emit_finding / emit_generic with reality_ledger_finding.
    """
    stub = _StubAuditEmit()
    with _planned_repo(tmp_path, {
        "PLAN-770-emit.md": (
            "---\nid: PLAN-770\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-770-emit.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                # 50h after created → high severity overrun
                ("b" * 40, "2026-04-03T10:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
            audit_emit_module=stub,
            session_id="s-test",
            project="p-test",
            emit_audit=True,
        )
    assert len(out) == 1
    # Typed emit fired exactly once
    assert len(stub.detected_calls) == 1, (
        f"expected 1 typed emit_estimate_drift_detected call; "
        f"got {len(stub.detected_calls)}: {stub.detected_calls}"
    )
    # Generic NOT used
    assert stub.generic_calls == [], (
        f"detector #7 fell back to generic emit_generic: {stub.generic_calls}"
    )
    # Int basis-points (Fix #2) — drift factor as int, NOT float
    call = stub.detected_calls[0]
    assert isinstance(call["drift_factor_compute_basis_points"], int)
    assert isinstance(call["drift_factor_owner_basis_points"], int)
    # Plan id propagated
    assert call["plan_id"] == "PLAN-770"
    # Severity in closed enum
    assert call["severity"] in ("low", "medium", "high")


def test_detect_07_emits_systematic_bias_via_typed_emitter(rl, tmp_path):
    """Codex Fix #1: 5+ same-direction findings → typed systematic_bias emit."""
    stub = _StubAuditEmit()
    plan_files = {}
    git_index = {}
    for i in range(6):
        slug = f"PLAN-{780 + i}-bias.md"
        plan_files[slug] = (
            f"---\nid: PLAN-{780 + i}\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        )
        git_index[f".claude/plans/{slug}"] = [
            ("a" * 40 + str(i), "2026-04-01T00:00:00+00:00", False),
            ("b" * 40 + str(i), "2026-04-05T00:00:00+00:00", False),
        ]
    with _planned_repo(tmp_path, plan_files) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index=git_index,
            calibration_csv=tmp_path / "calib.csv",
            audit_emit_module=stub,
            session_id="s-test",
            project="p-test",
            emit_audit=True,
        )
    assert len(out) >= 6
    # 6 detected + 1 systematic_bias
    assert len(stub.detected_calls) == 6
    assert len(stub.systematic_bias_calls) == 1
    sys_call = stub.systematic_bias_calls[0]
    assert sys_call["bias_direction"] in ("underestimate", "overestimate")
    assert isinstance(sys_call["avg_drift_factor_compute_basis_points"], int)
    assert isinstance(sys_call["avg_drift_factor_owner_basis_points"], int)


def test_detect_07_does_not_emit_when_emit_audit_false(rl, tmp_path):
    """When emit_audit=False (default), no typed emit fires (advisory-passive)."""
    stub = _StubAuditEmit()
    with _planned_repo(tmp_path, {
        "PLAN-771-passive.md": (
            "---\nid: PLAN-771\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n  owner_physical_min: 5\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-771-passive.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-03T10:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
            audit_emit_module=stub,
            emit_audit=False,
        )
    assert len(out) == 1
    assert stub.detected_calls == []
    assert stub.systematic_bias_calls == []


def test_detect_07_typed_emit_fail_open_on_missing_module(rl, tmp_path):
    """Codex Fix #1 fail-open: missing typed emitter → no crash."""

    class _MinimalStub:
        # Intentionally lacks emit_estimate_drift_detected
        pass

    with _planned_repo(tmp_path, {
        "PLAN-772-failopen.md": (
            "---\nid: PLAN-772\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-772-failopen.md": [
                ("a" * 40, "2026-04-01T08:00:00+00:00", False),
                ("b" * 40, "2026-04-03T10:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
            audit_emit_module=_MinimalStub(),
            emit_audit=True,
        )
    # Detector still emits findings (advisory side-effect-free path)
    assert isinstance(out, list)


# ===========================================================================
# Codex W1+W2 fix-pack — Fix #5 (status:done transition commit)
# ===========================================================================


def test_detect_07_status_done_transition_helper_present(rl):
    """Fix #5: helper API exists with documented signature."""
    assert hasattr(rl, "_git_status_done_transition")


def _git_init_with_commit(repo: Path, file_rel: str, content: str,
                          message: str, env: dict) -> str:
    """Initialize a git repo, create file, commit; return commit SHA."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=repo,
                   check=True, env=env)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo,
                   check=True, env=env)
    p = repo / file_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", file_rel], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo,
                   check=True, env=env)
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, env=env,
        capture_output=True, text=True,
    ).stdout.strip()
    return out


def test_detect_07_status_done_transition_finds_commit(rl, tmp_path):
    """Fix #5: helper locates the commit that adds `+status: done`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = os.environ.copy()
    # Disable any GPG signing in this throwaway repo
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env.pop("GPG_TTY", None)

    plan_rel = ".claude/plans/PLAN-555-fix5.md"
    # Commit 1: plan in draft
    sha1 = _git_init_with_commit(
        repo, plan_rel,
        "---\nid: PLAN-555\nstatus: draft\ncreated: 2026-04-01\n---\n# body\n",
        "PLAN-555 draft", env,
    )
    # Commit 2: flip to done
    (repo / plan_rel).write_text(
        "---\nid: PLAN-555\nstatus: done\ncreated: 2026-04-01\n---\n# body\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", plan_rel], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "close PLAN-555"],
                   cwd=repo, check=True, env=env)
    sha2 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, env=env,
        capture_output=True, text=True,
    ).stdout.strip()

    transition = rl._git_status_done_transition(repo, plan_rel)
    assert transition is not None
    assert transition[0] == sha2, (
        f"expected closeout SHA {sha2}; got {transition[0]} (sha1={sha1})"
    )
    # ISO date is committer-date format
    assert "T" in transition[1]


def test_detect_07_status_done_transition_no_flip_returns_none(rl, tmp_path):
    """Plan never flipped to done → helper returns None."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env.pop("GPG_TTY", None)
    plan_rel = ".claude/plans/PLAN-556-still-draft.md"
    _git_init_with_commit(
        repo, plan_rel,
        "---\nid: PLAN-556\nstatus: draft\ncreated: 2026-04-01\n---\n# body\n",
        "PLAN-556 draft", env,
    )
    transition = rl._git_status_done_transition(repo, plan_rel)
    assert transition is None


def test_detect_07_skip_when_span_zero(rl, tmp_path):
    """Fix #5 edge: plan created and closed in same commit → span=0 → skipped."""
    # Synthetic git_log_index with single commit at midnight matching created.
    with _planned_repo(tmp_path, {
        "PLAN-557-onecommit.md": (
            "---\nid: PLAN-557\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        out = rl.detect_estimate_drift(
            repo_root=repo,
            git_log_index={".claude/plans/PLAN-557-onecommit.md": [
                ("a" * 40, "2026-04-01T00:00:00+00:00", False),
            ]},
            calibration_csv=tmp_path / "calib.csv",
        )
    # span = 0 → skipped silently (no crash, no finding)
    assert out == []


def test_detect_07_uses_status_done_transitions_arg(rl, tmp_path):
    """Fix #5 test injection: status_done_transitions overrides last-commit logic."""
    with _planned_repo(tmp_path, {
        "PLAN-558-mock-tx.md": (
            "---\nid: PLAN-558\nstatus: done\ncreated: 2026-04-01\n"
            "estimate:\n  compute_hours: 1-2\n---\n"
        ),
    }) as repo:
        # Mock the transition: 60h after created = 4× drift
        out = rl.detect_estimate_drift(
            repo_root=repo,
            status_done_transitions={
                ".claude/plans/PLAN-558-mock-tx.md": (
                    "c" * 40, "2026-04-03T12:00:00+00:00",
                ),
            },
            calibration_csv=tmp_path / "calib.csv",
        )
    assert len(out) == 1
    # Span = 60h vs estimate mid 1.5h = 40× → high severity
    assert out[0]["severity"] == "high"
    assert out[0]["_extra"]["transition_commit_sha"] == "c" * 40
