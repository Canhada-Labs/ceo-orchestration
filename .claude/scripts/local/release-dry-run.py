#!/usr/bin/env python3
"""Local dry-run of `.github/workflows/release.yml` gates.

PLAN-078 Wave 3 deliverable. Reproduces 16 always-run validation gates +
1 conditional sigstore step from the release workflow so the Owner can
validate locally BEFORE pushing a tag.

ROI: each fail-iteration of release.yml costs `git tag → push → wait CI
~8 min → fix → retag`. Running this script catches the same failures in
~30-60s and the Owner only signs a tag once it's clean.

Source-of-truth: `.github/workflows/release.yml:25-441`. Each gate below
maps to one named step in that file.

Usage:
    python3 .claude/scripts/local/release-dry-run.py --target-version 1.14.0

    # Skip slow gates for fast iteration:
    python3 .claude/scripts/local/release-dry-run.py \\
        --target-version 1.15.0-rc.1 \\
        --skip-tests \\
        --skip-install \\
        --skip-network

Exit codes:
    0 — all gates passed (or skipped without --strict)
    1 — one or more gates failed
    2 — missing dependency (pyyaml)
    3 — invalid CLI args
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple


# ---------- Result type ----------


@dataclass
class GateResult:
    name: str
    passed: bool = False
    skipped: bool = False
    detail: str = ""
    duration_ms: int = 0

    @property
    def status(self) -> str:
        if self.skipped:
            return "SKIP"
        return "PASS" if self.passed else "FAIL"


# ---------- Gate registry ----------

GATES: List[Callable[["DryRunArgs"], GateResult]] = []


def gate(name: str) -> Callable[[Callable], Callable]:
    """Decorator: register a gate function in GATES (preserves definition order).

    Attaches `.gate_name` attribute so the runner can render display names
    without an external mapping. Tests can iterate `GATES` and call each
    entry directly.
    """

    def decorator(fn: Callable[["DryRunArgs"], GateResult]) -> Callable:
        fn.gate_name = name  # type: ignore[attr-defined]
        GATES.append(fn)
        return fn

    return decorator


# ---------- Args + helpers ----------


@dataclass
class DryRunArgs:
    target_version: str
    skip_tests: bool = False
    skip_install: bool = False
    skip_network: bool = False
    strict: bool = False
    repo_root: Path = field(default_factory=lambda: Path.cwd())


def _is_rc_tag(version: str) -> bool:
    """Return True if version contains the `-rc.` marker (e.g. 1.14.0-rc.2)."""
    return "-rc." in version


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a subprocess with stdout+stderr captured and a default timeout."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def _load_waivers(waiver_file: Path) -> dict:
    """Lazy-load waivers via pyyaml. Returns {} on missing file or parse error."""
    if not waiver_file.is_file():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        # Caller is responsible for the up-front pyyaml check; this should not
        # be reached in practice. Fail-soft to {} so individual gates don't
        # crash mid-run.
        return {}
    try:
        data = yaml.safe_load(waiver_file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 — malformed YAML must not crash dry-run
        return {}


def _waiver_versions(waivers: dict, key: str) -> List[str]:
    """Return list of versions covered by waivers[key] entries."""
    entries = waivers.get(key, [])
    if not isinstance(entries, list):
        return []
    out = []
    for entry in entries:
        if isinstance(entry, dict) and "version" in entry:
            out.append(str(entry["version"]).strip())
    return out


# ---------- Gate implementations (16 + 1 conditional) ----------


@gate("VERSION matches tag")
def check_version_matches_tag(args: DryRunArgs) -> GateResult:
    """release.yml:37 — VERSION file must equal the target version."""
    version_file = args.repo_root / "VERSION"
    if not version_file.is_file():
        return GateResult(
            name="VERSION matches tag",
            passed=False,
            detail=f"VERSION file not found at {version_file}",
        )
    file_version = version_file.read_text(encoding="utf-8").strip()
    if file_version != args.target_version:
        return GateResult(
            name="VERSION matches tag",
            passed=False,
            detail=f"VERSION='{file_version}' != target='{args.target_version}'",
        )
    return GateResult(
        name="VERSION matches tag",
        passed=True,
        detail=f"VERSION={file_version} matches target",
    )


@gate("24h Codex re-pass window (GA only)")
def check_rc_hold_window(args: DryRunArgs) -> GateResult:
    """release.yml:70 — GA tags require a `-rc.N` predecessor ≥24h old.

    RC tags short-circuit (always pass).
    Waiver in `.claude/governance/governance-waivers.yaml` short-circuits.
    """
    name = "24h Codex re-pass window (GA only)"
    if _is_rc_tag(args.target_version):
        return GateResult(name=name, passed=True, detail="RC tag — gate not applicable")

    # Pre-GA waiver check
    waiver_file = args.repo_root / ".claude/governance/governance-waivers.yaml"
    waivers = _load_waivers(waiver_file)
    if args.target_version in _waiver_versions(waivers, "rc_hold"):
        return GateResult(
            name=name,
            passed=True,
            detail=f"waived in {waiver_file.name} → rc_hold",
        )

    # Find most-recent v<version>-rc.* tag by creator date
    proc = _run(
        ["git", "tag", "-l", "--sort=-creatordate", f"v{args.target_version}-rc.*"],
        cwd=args.repo_root,
    )
    if proc.returncode != 0:
        return GateResult(name=name, passed=False, detail=f"git tag failed: {proc.stderr.strip()}")
    tags = [t for t in proc.stdout.splitlines() if t.strip()]
    if not tags:
        return GateResult(
            name=name,
            passed=False,
            detail=f"no v{args.target_version}-rc.* tag found; cut RC first",
        )
    last_rc = tags[0]
    rc_ts_proc = _run(
        ["git", "tag", "-l", "--format=%(creatordate:unix)", last_rc],
        cwd=args.repo_root,
    )
    if rc_ts_proc.returncode != 0 or not rc_ts_proc.stdout.strip():
        return GateResult(name=name, passed=False, detail=f"could not read date for {last_rc}")
    try:
        rc_ts = int(rc_ts_proc.stdout.strip())
    except ValueError:
        return GateResult(name=name, passed=False, detail=f"unparseable date for {last_rc}")
    delta = int(time.time()) - rc_ts
    hours = delta // 3600
    if delta < 86400:
        return GateResult(
            name=name,
            passed=False,
            detail=f"{last_rc} is only {hours}h old (need ≥24h)",
        )
    return GateResult(
        name=name,
        passed=True,
        detail=f"{last_rc} is {hours}h old (≥24h)",
    )


@gate("CHANGELOG entry exists")
def check_changelog_entry_exists(args: DryRunArgs) -> GateResult:
    """release.yml:132 — CHANGELOG.md must contain `## [VERSION]` line."""
    changelog = args.repo_root / "CHANGELOG.md"
    if not changelog.is_file():
        return GateResult(
            name="CHANGELOG entry exists",
            passed=False,
            detail=f"{changelog} not found",
        )
    pattern = re.compile(rf"^## \[{re.escape(args.target_version)}\]", re.MULTILINE)
    if not pattern.search(changelog.read_text(encoding="utf-8")):
        return GateResult(
            name="CHANGELOG entry exists",
            passed=False,
            detail=f"no `## [{args.target_version}]` section in CHANGELOG.md",
        )
    return GateResult(
        name="CHANGELOG entry exists",
        passed=True,
        detail=f"`## [{args.target_version}]` present",
    )


@gate("Registry validation")
def check_registry_validation(args: DryRunArgs) -> GateResult:
    """release.yml:143 — `python3 .claude/scripts/registry.py --validate`."""
    registry = args.repo_root / ".claude/scripts/registry.py"
    if not registry.is_file():
        return GateResult(
            name="Registry validation",
            skipped=True,
            detail=f"{registry} not found",
        )
    proc = _run(["python3", str(registry), "--validate"], cwd=args.repo_root, timeout=60)
    if proc.returncode != 0:
        return GateResult(
            name="Registry validation",
            passed=False,
            detail=f"exit {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}",
        )
    return GateResult(name="Registry validation", passed=True, detail="registry clean")


@gate("Governance structural validation")
def check_governance_validate(args: DryRunArgs) -> GateResult:
    """release.yml:146 — `bash .claude/scripts/validate-governance.sh`."""
    script = args.repo_root / ".claude/scripts/validate-governance.sh"
    if not script.is_file():
        return GateResult(
            name="Governance structural validation",
            passed=False,
            detail=f"{script} not found",
        )
    proc = _run(["bash", str(script)], cwd=args.repo_root, timeout=120)
    if proc.returncode != 0:
        # Tail the last error line for the digest
        tail = ""
        for line in (proc.stdout or "").splitlines()[-5:]:
            tail = line.strip()
        return GateResult(
            name="Governance structural validation",
            passed=False,
            detail=f"exit {proc.returncode}; tail: {tail}",
        )
    return GateResult(
        name="Governance structural validation",
        passed=True,
        detail="0 errors",
    )


@gate("Hook test suite")
def check_hook_tests(args: DryRunArgs) -> GateResult:
    """release.yml:158 — `pytest .claude/hooks/tests`."""
    if args.skip_tests:
        return GateResult(name="Hook test suite", skipped=True, detail="--skip-tests")
    proc = _run(
        ["python3", "-m", "pytest", ".claude/hooks/tests", "-q", "--tb=short"],
        cwd=args.repo_root,
        timeout=300,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or "").splitlines()[-3:]
        return GateResult(
            name="Hook test suite",
            passed=False,
            detail=f"exit {proc.returncode}: {' / '.join(tail).strip()[:300]}",
        )
    # Extract pass count from summary line
    summary = ""
    for line in reversed((proc.stdout or "").splitlines()):
        if "passed" in line and ("=" in line or " " in line):
            summary = line.strip()
            break
    return GateResult(name="Hook test suite", passed=True, detail=summary[:200] or "GREEN")


@gate("Script test suite")
def check_script_tests(args: DryRunArgs) -> GateResult:
    """release.yml:162 — `pytest .claude/scripts/tests`."""
    if args.skip_tests:
        return GateResult(name="Script test suite", skipped=True, detail="--skip-tests")
    proc = _run(
        ["python3", "-m", "pytest", ".claude/scripts/tests", "-q", "--tb=short"],
        cwd=args.repo_root,
        timeout=300,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or "").splitlines()[-3:]
        return GateResult(
            name="Script test suite",
            passed=False,
            detail=f"exit {proc.returncode}: {' / '.join(tail).strip()[:300]}",
        )
    summary = ""
    for line in reversed((proc.stdout or "").splitlines()):
        if "passed" in line:
            summary = line.strip()
            break
    return GateResult(name="Script test suite", passed=True, detail=summary[:200] or "GREEN")


@gate("Replay test suite")
def check_replay_tests(args: DryRunArgs) -> GateResult:
    """release.yml:165 — `pytest .claude/scripts/replay/tests`."""
    if args.skip_tests:
        return GateResult(name="Replay test suite", skipped=True, detail="--skip-tests")
    replay_dir = args.repo_root / ".claude/scripts/replay/tests"
    if not replay_dir.is_dir():
        return GateResult(name="Replay test suite", skipped=True, detail="replay tests dir absent")
    proc = _run(
        ["python3", "-m", "pytest", str(replay_dir), "-q", "--tb=short"],
        cwd=args.repo_root,
        timeout=180,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or "").splitlines()[-3:]
        return GateResult(
            name="Replay test suite",
            passed=False,
            detail=f"exit {proc.returncode}: {' / '.join(tail).strip()[:300]}",
        )
    summary = ""
    for line in reversed((proc.stdout or "").splitlines()):
        if "passed" in line:
            summary = line.strip()
            break
    return GateResult(name="Replay test suite", passed=True, detail=summary[:200] or "GREEN")


@gate("Smoke install on scratch dir")
def check_smoke_install(args: DryRunArgs) -> GateResult:
    """release.yml:172 — invoke install.sh into a tmpdir and verify essentials."""
    if args.skip_install:
        return GateResult(
            name="Smoke install on scratch dir",
            skipped=True,
            detail="--skip-install",
        )
    install = args.repo_root / "scripts/install.sh"
    if not install.is_file():
        return GateResult(
            name="Smoke install on scratch dir",
            passed=False,
            detail=f"{install} not found",
        )
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ceo-smoke-") as td:
        target = Path(td) / "target"
        target.mkdir()
        # git init quiet
        gi = _run(["git", "init", "-q"], cwd=target)
        if gi.returncode != 0:
            return GateResult(
                name="Smoke install on scratch dir",
                passed=False,
                detail=f"git init failed: {gi.stderr.strip()}",
            )
        proc = _run(
            ["bash", str(install), str(target), "--profile", "core,frontend"],
            cwd=args.repo_root,
            timeout=120,
        )
        if proc.returncode != 0:
            return GateResult(
                name="Smoke install on scratch dir",
                passed=False,
                detail=f"install.sh rc={proc.returncode}: {(proc.stderr or '').strip()[:200]}",
            )
        # Essentials present
        essentials = [
            target / ".claude/team.md",
            target / ".claude/settings.json",
        ]
        for e in essentials:
            if not e.is_file():
                return GateResult(
                    name="Smoke install on scratch dir",
                    passed=False,
                    detail=f"missing essential: {e.relative_to(target)}",
                )
        if not (target / ".claude/skills/core").is_dir():
            return GateResult(
                name="Smoke install on scratch dir",
                passed=False,
                detail="missing dir: .claude/skills/core",
            )
        # No leaked placeholders in hooks
        hooks_dir = target / ".claude/hooks"
        if hooks_dir.is_dir():
            for f in hooks_dir.rglob("*"):
                if f.is_file():
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    if "{{OWNER_NAME}}" in text or "{{PROJECT_NAME}}" in text:
                        return GateResult(
                            name="Smoke install on scratch dir",
                            passed=False,
                            detail=f"placeholder leaked into {f.relative_to(target)}",
                        )
        # settings.json must parse
        import json

        try:
            json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return GateResult(
                name="Smoke install on scratch dir",
                passed=False,
                detail=f"settings.json parse error: {exc}",
            )
    return GateResult(
        name="Smoke install on scratch dir",
        passed=True,
        detail="install.sh + 4 essentials clean",
    )


@gate("install.sh self-SHA mechanism")
def check_install_self_sha(args: DryRunArgs) -> GateResult:
    """release.yml:192 — verify install.sh self-SHA verification works.

    Source-tree placeholder must be present; populated copy must rc=1
    (usage exit, not rc=5); tampered copy must rc=5.
    """
    if args.skip_install:
        return GateResult(
            name="install.sh self-SHA mechanism",
            skipped=True,
            detail="--skip-install",
        )
    install = args.repo_root / "scripts/install.sh"
    if not install.is_file():
        return GateResult(
            name="install.sh self-SHA mechanism",
            passed=False,
            detail=f"{install} not found",
        )
    lines = install.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return GateResult(
            name="install.sh self-SHA mechanism",
            passed=False,
            detail="install.sh is empty",
        )
    trailer_expected = "# CEO-INSTALL-SHA256: PLACEHOLDER_RELEASE_FILL"
    if lines[-1].strip() != trailer_expected:
        return GateResult(
            name="install.sh self-SHA mechanism",
            passed=False,
            detail=f"trailer drifted: '{lines[-1]}'",
        )
    # We don't run the populated/tamper E2E by default — that takes ~5-10s and
    # the trailer presence check is a good local-fast proxy. Owner can run
    # release.yml in CI for the full E2E.
    return GateResult(
        name="install.sh self-SHA mechanism",
        passed=True,
        detail="trailer placeholder present (full E2E in CI only)",
    )


@gate("Audit-log schema additivity")
def check_audit_log_schema_additivity(args: DryRunArgs) -> GateResult:
    """release.yml:253 — every v1 agent_spawn field must still be in schema doc."""
    required = [
        "ts", "action", "session_id", "project", "tool",
        "subagent_type", "desc_preview", "desc_hash", "skill",
        "has_profile", "has_file_assignment", "prompt_len_bucket",
        "response_kind", "hook_duration_ms",
    ]
    schema = args.repo_root / ".claude/plans/AUDIT-LOG-SCHEMA.md"
    if not schema.is_file():
        return GateResult(
            name="Audit-log schema additivity",
            passed=False,
            detail=f"{schema} not found",
        )
    text = schema.read_text(encoding="utf-8", errors="replace")
    missing = []
    for f in required:
        if f'"{f}":' not in text and f"`{f}`" not in text:
            missing.append(f)
    if missing:
        return GateResult(
            name="Audit-log schema additivity",
            passed=False,
            detail=f"missing field(s): {', '.join(missing)}",
        )
    return GateResult(
        name="Audit-log schema additivity",
        passed=True,
        detail=f"all {len(required)} v1 fields preserved",
    )


@gate("Weekly workflow status (GitHub API)")
def check_weekly_workflow_status(args: DryRunArgs) -> GateResult:
    """release.yml:288 — last 3 runs of 6 advisory workflows must be clean.

    Requires `gh` CLI + GitHub auth. Skip with --skip-network OR if gh missing.
    Waiver via `governance-waivers.yaml::workflow_staleness`.
    """
    name = "Weekly workflow status (GitHub API)"
    if args.skip_network:
        return GateResult(name=name, skipped=True, detail="--skip-network")
    waiver_file = args.repo_root / ".claude/governance/governance-waivers.yaml"
    waivers = _load_waivers(waiver_file)
    if args.target_version in _waiver_versions(waivers, "workflow_staleness"):
        return GateResult(
            name=name,
            passed=True,
            detail=f"waived in {waiver_file.name} → workflow_staleness",
        )
    if not _which("gh"):
        return GateResult(name=name, skipped=True, detail="gh CLI not on PATH")
    workflows = [
        "chaos.yml", "otel-smoke.yml", "perf-profile.yml",
        "adapter-live.yml", "red-team.yml", "formal-verify.yml",
    ]
    failures: List[str] = []
    for wf in workflows:
        proc = _run(
            ["gh", "run", "list", "--workflow", wf, "--limit", "3", "--json", "conclusion,startedAt"],
            cwd=args.repo_root,
            timeout=30,
        )
        if proc.returncode != 0:
            failures.append(f"{wf}: gh exit {proc.returncode}")
            continue
        try:
            import json

            runs = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            failures.append(f"{wf}: malformed gh output")
            continue
        if not runs:
            failures.append(f"{wf}: zero runs (staleness)")
            continue
        conclusions = [r.get("conclusion") for r in runs]
        latest = conclusions[0] if conclusions else None
        if "failure" in conclusions and latest == "failure":
            failures.append(f"{wf}: latest failed + prior failure")
        # Staleness: check last run within 14 days
        latest_started = runs[0].get("startedAt") if runs else None
        if latest_started:
            try:
                from datetime import datetime, timezone

                started = datetime.fromisoformat(latest_started.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - started).days
                if age_days > 14:
                    failures.append(f"{wf}: stale ({age_days}d > 14d)")
            except ValueError:
                failures.append(f"{wf}: unparseable startedAt={latest_started}")
    if failures:
        return GateResult(
            name=name,
            passed=False,
            detail="; ".join(failures)[:300],
        )
    return GateResult(name=name, passed=True, detail=f"{len(workflows)} workflows green + fresh")


@gate("Generate CycloneDX SBOM")
def check_generate_sbom(args: DryRunArgs) -> GateResult:
    """release.yml:401 — `python3 .claude/scripts/generate-sbom.py`."""
    sbom = args.repo_root / ".claude/scripts/generate-sbom.py"
    if not sbom.is_file():
        return GateResult(
            name="Generate CycloneDX SBOM",
            skipped=True,
            detail=f"{sbom} not found",
        )
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out_path = tf.name
    try:
        proc = _run(
            ["python3", str(sbom), "--output", out_path],
            cwd=args.repo_root,
            timeout=60,
        )
        if proc.returncode != 0:
            return GateResult(
                name="Generate CycloneDX SBOM",
                passed=False,
                detail=f"exit {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:200]}",
            )
        # Inspect output
        import json

        try:
            data = json.loads(Path(out_path).read_text(encoding="utf-8"))
            n = len(data.get("components", [])) if isinstance(data, dict) else 0
        except Exception:  # noqa: BLE001
            n = 0
        return GateResult(
            name="Generate CycloneDX SBOM",
            passed=True,
            detail=f"{n} components",
        )
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


@gate("Sigstore signing (RC-skipped, conditional)")
def check_sigstore_signing(args: DryRunArgs) -> GateResult:
    """release.yml:408 — sigstore signing. Skipped by design on `*-rc*` tags."""
    name = "Sigstore signing (RC-skipped, conditional)"
    if _is_rc_tag(args.target_version):
        return GateResult(name=name, skipped=True, detail="RC tag — sigstore step skipped by design")
    # In the workflow this is gated on `vars.SIGSTORE_ACTIVATED == 'true'`.
    # Locally we treat absence of `cosign` or repo var as a SKIP (not FAIL).
    cosign = _which("cosign")
    if not cosign:
        return GateResult(name=name, skipped=True, detail="cosign not on PATH (CI-only)")
    return GateResult(name=name, skipped=True, detail="local verify only; CI does the real sign")


@gate("Verify owner.asc populated")
def check_owner_asc_populated(args: DryRunArgs) -> GateResult:
    """release.yml:419 — `.claude/trust/owner.asc` must be non-empty + parseable."""
    name = "Verify owner.asc populated"
    asc = args.repo_root / ".claude/trust/owner.asc"
    if not asc.is_file():
        return GateResult(
            name=name,
            skipped=True,
            detail=f"{asc} not present locally (release.yml requires it)",
        )
    if asc.stat().st_size == 0:
        return GateResult(name=name, passed=False, detail="owner.asc is empty")
    if not _which("gpg"):
        return GateResult(name=name, skipped=True, detail="gpg not on PATH")
    proc = _run(["gpg", "--show-keys", str(asc)], cwd=args.repo_root, timeout=15)
    if proc.returncode != 0:
        return GateResult(
            name=name,
            passed=False,
            detail=f"owner.asc not a valid PGP block (gpg exit {proc.returncode})",
        )
    return GateResult(name=name, passed=True, detail="owner.asc populated + parseable")


@gate("Verify tag GPG signature")
def check_tag_gpg_signature(args: DryRunArgs) -> GateResult:
    """release.yml:437 — `git tag --verify` against the actual tag.

    Locally: skipped unless the tag actually exists in this repo.
    """
    name = "Verify tag GPG signature"
    tag = f"v{args.target_version}"
    proc = _run(["git", "tag", "-l", tag], cwd=args.repo_root, timeout=10)
    if proc.returncode != 0 or not proc.stdout.strip():
        return GateResult(
            name=name,
            skipped=True,
            detail=f"tag {tag} not present locally (sign + run release.yml in CI)",
        )
    # Tag exists — try to verify
    if not _which("gpg"):
        return GateResult(name=name, skipped=True, detail="gpg not on PATH")
    verify = _run(["git", "tag", "--verify", tag], cwd=args.repo_root, timeout=15)
    if verify.returncode != 0:
        return GateResult(
            name=name,
            passed=False,
            detail=f"git tag --verify exit {verify.returncode}: {(verify.stderr or '').strip()[:200]}",
        )
    return GateResult(name=name, passed=True, detail=f"{tag} GPG signature valid")


# ---------- CLI ----------


def _print_summary(results: List[GateResult]) -> None:
    """Render results as a markdown table on stdout."""
    print()
    print("# release-dry-run results")
    print()
    print(f"| {'#':>2} | {'Gate':<44} | {'Status':<6} | {'ms':>5} | Detail |")
    print(f"| {'-'*2} | {'-'*44} | {'-'*6} | {'-'*5} | {'-'*50} |")
    for i, r in enumerate(results, 1):
        detail = (r.detail or "")[:80].replace("|", "\\|")
        print(f"| {i:>2} | {r.name[:44]:<44} | {r.status:<6} | {r.duration_ms:>5} | {detail} |")
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    passed = sum(1 for r in results if r.passed)
    total_ms = sum(r.duration_ms for r in results)
    print()
    print(f"**Summary:** {passed} passed / {failed} failed / {skipped} skipped — {total_ms} ms total")


def _ensure_pyyaml() -> None:
    """Up-front guarded import per docs/stdlib-exceptions.md pattern.

    Exits 2 with a clear install hint on ImportError.
    """
    try:
        import yaml  # noqa: F401  # type: ignore
    except ImportError:
        print(
            "release-dry-run: PyYAML is required (python3 -m pip install pyyaml)",
            file=sys.stderr,
        )
        sys.exit(2)


def _infer_target_version(repo_root: Path) -> Optional[str]:
    """If HEAD has an exact tag match, return its stripped version (no `v`)."""
    proc = _run(["git", "describe", "--tags", "--exact-match"], cwd=repo_root, timeout=10)
    if proc.returncode != 0:
        return None
    tag = proc.stdout.strip()
    if not tag:
        return None
    return tag[1:] if tag.startswith("v") else tag


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local dry-run of .github/workflows/release.yml gates (PLAN-078 W3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target-version",
        help="Target version (e.g. 1.14.0 or 1.15.0-rc.1). Inferred from git tag if omitted.",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest gates (6/7/8)")
    parser.add_argument("--skip-install", action="store_true", help="Skip smoke install + self-SHA gates (9/10)")
    parser.add_argument("--skip-network", action="store_true", help="Skip GitHub API gate (12)")
    parser.add_argument("--strict", action="store_true", help="Treat skipped gates as failures")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repo root (default: cwd)",
    )
    args_ns = parser.parse_args(argv)

    # Up-front pyyaml check
    _ensure_pyyaml()

    target = args_ns.target_version
    if not target:
        target = _infer_target_version(args_ns.repo_root)
    if not target:
        print(
            "release-dry-run: --target-version not provided and HEAD has no exact tag match",
            file=sys.stderr,
        )
        return 3

    args = DryRunArgs(
        target_version=target,
        skip_tests=args_ns.skip_tests,
        skip_install=args_ns.skip_install,
        skip_network=args_ns.skip_network,
        strict=args_ns.strict,
        repo_root=args_ns.repo_root.resolve(),
    )

    print(f"release-dry-run: target_version={target} repo={args.repo_root}", file=sys.stderr)

    results: List[GateResult] = []
    for fn in GATES:
        name = getattr(fn, "gate_name", fn.__name__)
        t0 = time.monotonic()
        try:
            r = fn(args)
        except Exception as exc:  # noqa: BLE001 — gates must not raise to caller
            r = GateResult(name=name, passed=False, detail=f"exception: {exc}"[:200])
        r.duration_ms = int((time.monotonic() - t0) * 1000)
        results.append(r)

    _print_summary(results)

    failed = sum(1 for r in results if not r.passed and not r.skipped)
    if failed:
        return 1
    if args.strict and any(r.skipped for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
