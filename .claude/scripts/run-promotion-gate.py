#!/usr/bin/env python3
"""run-promotion-gate.py — PLAN-081 Phase 4 deliverable.

Pair-Rail promotion gate: runs the locked corpus through Codex MCP +
applies the 2-pass-with-triage logic per ADR-108 §Operational + ADR-111
governance. Emits ``pair_rail_promotion`` audit event + MAY
auto-flip routing-matrix.yaml entries from review-only (Phase 1) to
coder mode (Phase 2 of the Pair-Rail timeline) when verdict == PASS or
PASS_AFTER_RETRY.

## Usage

    python3 .claude/scripts/run-promotion-gate.py [--dry-run] [--parallel N]

Flags:
    --dry-run              Skip routing-matrix.yaml mutation; emit
                           verdict only. Default behavior at Phase 4
                           ship.
    --parallel N           Run N fixtures concurrently (default 1
                           sequential). R1 C8: optional; sequential
                           recommended for U5 timeout-flake mitigation.

Env:
    CEO_PHASE_AUTO_FLIP_DRY_RUN=1   Same as --dry-run (CI-friendly).
    CEO_PHASE_4_PARTIAL_OK=1        Permit run with corpus_n < 15
                                     (emits manual_triage=True; for
                                     development; see ADR-111 §5).
    CEO_CODEX_CLI_PIN=<semver>      Override Codex CLI version pin
                                     check (Phase 6 deliverable;
                                     advisory at Phase 4).

## Verdict logic (per ADR-108 §Operational + R1 C6)

    Pass 1: Run all N fixtures with 240s timeout + retry-on-timeout
            per fixture. Compute catch_rate, fp_rate, schema_adherence.

    If catch_rate == N/N AND fp_rate <= 15% AND schema_adherence == 100%:
        verdict = PASS
        auto-flip if not dry-run.

    Elif catch_rate == (N-1)/N with 1 timeout/parse-error in Pass 1:
        Pass 2: Re-run THE 1 FAILED fixture with 240s + retry.
        If 1/1 → verdict = PASS_AFTER_RETRY (auto-flip if not dry-run).
        Else → verdict = TRIAGE (manual triage artifact emitted).

    Elif (N-3) <= catch_rate < (N-1):
        verdict = TRIAGE (manual triage artifact emitted).

    Else (catch_rate < N-3):
        verdict = FAIL.

## Concurrency / atomicity (per Codex iter 1 R-NEW-5)

The gate acquires a filelock at
``~/.claude/projects/<project>/state/pair-rail-promotion.lock`` for
the entire run. Recording at run start:
    - git rev-parse HEAD → git_head_sha (pinned at start)
    - corpus MANIFEST SHA-256 (pinned at start)
    - pair_rail_promotion_run_id (UUID4 hex)

At verdict flip time:
    - assert git HEAD unchanged (no rebase mid-run)
    - assert corpus MANIFEST SHA unchanged (no fixture-mutation)
    - atomic write to routing-matrix.yaml via tmp+rename

Stdlib only. Python ≥3.9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GATE_VERSION = "1.0.0-rc.1"
TARGET_CORPUS_N = 15  # ADR-111 + R1 C4
PASS_1_TIMEOUT_S = 240
RETRY_TIMEOUT_S = 240
WARMUP_TIMEOUT_S = 5
FP_RATE_THRESHOLD = 0.15
SCHEMA_ADHERENCE_REQUIRED = 1.0

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = DEFAULT_REPO_ROOT / ".claude" / "plans" / "PLAN-081" / "corpus" / "locked"
DEFAULT_MANIFEST_PATH = DEFAULT_CORPUS_DIR / "MANIFEST.md"
DEFAULT_ROUTING_MATRIX = DEFAULT_REPO_ROOT / ".claude" / "dispatcher" / "routing-matrix.yaml"


# ---------------------------------------------------------------------
# Datatypes
# ---------------------------------------------------------------------


class GateError(Exception):
    """Raised on unrecoverable gate errors. Caller decides verdict."""


# ---------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------


def compute_sha256(path: Path) -> str:
    """Return SHA-256 hex digest of file bytes."""
    if not path.exists():
        raise GateError(f"path not found for SHA: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    """Parse the corpus MANIFEST.md fixtures section.

    Returns a list of fixture dicts (id, stratum, severity, scope,
    rubric_violation_id, expected_verdict, path, sha256, added_at,
    retired, retired_at, reason).

    Phase 4 ship: returns [] (zero fixtures authored). Phase 4-bis
    populates the ``fixtures:`` YAML block.
    """
    if not manifest_path.exists():
        raise GateError(f"MANIFEST not found: {manifest_path}")
    text = manifest_path.read_text(encoding="utf-8")
    # Find the ```yaml fixtures: ... ``` block
    fixtures_match = re.search(
        r"```yaml\s*\nfixtures:\s*\n(.*?)```",
        text,
        re.DOTALL,
    )
    if not fixtures_match:
        return []
    yaml_body = fixtures_match.group(1)
    # If the body is just `[]` or empty, no fixtures yet (Phase 4 ship).
    if yaml_body.strip() in ("", "[]"):
        return []
    # Minimal YAML parser inline (stdlib-only). For Phase 4-bis,
    # the proper loader from routing-matrix-loader.py can be reused.
    fixtures: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw_line in yaml_body.splitlines():
        line = raw_line.split("#", 1)[0] if "#" in raw_line else raw_line
        line = line.rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 2 and stripped.startswith("- id:"):
            if current is not None and "id" in current:
                fixtures.append(current)
            current = {}
            _, _, val = stripped.partition(":")
            current["id"] = val.strip()
        elif indent == 4 and current is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            v = val.strip()
            # Coerce booleans
            if v == "true":
                v = True
            elif v == "false":
                v = False
            elif v == "null":
                v = None
            current[key.strip()] = v
    if current is not None and "id" in current:
        fixtures.append(current)
    return fixtures


def filter_active_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Exclude retired fixtures from active corpus."""
    return [f for f in fixtures if not f.get("retired", False)]


# ---------------------------------------------------------------------
# Codex CLI invocation
# ---------------------------------------------------------------------


def warmup_codex_cli(timeout_s: int = WARMUP_TIMEOUT_S) -> bool:
    """Pre-flight Codex CLI warm-up call (R1 C8). Empty prompt, ≤5s.

    Returns True on success. False on any error (caller logs but
    continues; warm-up is advisory).
    """
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            timeout=timeout_s,
            text=True,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def get_codex_cli_version() -> str:
    """Return Codex CLI version string (best-effort; '' on error)."""
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            timeout=WARMUP_TIMEOUT_S,
            text=True,
        )
        if result.returncode == 0:
            # Parse version from stdout (first line, after 'codex' or version-like token)
            for line in result.stdout.splitlines():
                m = re.search(r"(\d+\.\d+\.\d+(?:[-+][\w.]+)?)", line)
                if m:
                    return m.group(1)
        return ""
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


# ---------------------------------------------------------------------
# Per-fixture review (Codex MCP invocation)
# ---------------------------------------------------------------------


def review_fixture(
    fixture: Dict[str, Any],
    repo_root: Path,
    timeout_s: int = PASS_1_TIMEOUT_S,
) -> Dict[str, Any]:
    """Run Codex review against ONE fixture. Returns review verdict dict.

    Phase 4 ship: stub implementation that emits a "framework-only"
    verdict because no fixtures are authored yet. Phase 4-bis wires
    actual Codex MCP invocation via _lib/adapters/codex.make_invoke_command
    + parse_verdict.

    Returns:
        {"fixture_id": str, "verdict": str, "elapsed_s": float,
         "error": Optional[str]}
        verdict ∈ {"PASS", "BLOCK", "ADVISORY", "TIMEOUT", "MALFORMED"}.
    """
    t0 = time.monotonic()
    fixture_id = fixture.get("id", "unknown")
    fixture_path_str = fixture.get("path", "")
    if not fixture_path_str:
        return {
            "fixture_id": fixture_id,
            "verdict": "MALFORMED",
            "elapsed_s": 0.0,
            "error": "missing fixture path",
        }
    fixture_path = repo_root / fixture_path_str
    if not fixture_path.exists():
        return {
            "fixture_id": fixture_id,
            "verdict": "MALFORMED",
            "elapsed_s": 0.0,
            "error": f"fixture file not found: {fixture_path}",
        }
    expected_sha = fixture.get("sha256", "")
    actual_sha = compute_sha256(fixture_path)
    if expected_sha and expected_sha != actual_sha:
        return {
            "fixture_id": fixture_id,
            "verdict": "MALFORMED",
            "elapsed_s": time.monotonic() - t0,
            "error": f"SHA mismatch (manifest={expected_sha[:16]}, actual={actual_sha[:16]})",
        }
    # Phase 4 ship: stub. Phase 4-bis wires real Codex via
    #   from _lib.adapters import codex
    #   prompt = codex.make_invoke_command(...)
    #   stdout = subprocess.run(prompt, ...)
    #   verdict_dict = codex.parse_verdict(stdout)
    return {
        "fixture_id": fixture_id,
        "verdict": "ADVISORY",  # Phase 4 stub
        "elapsed_s": time.monotonic() - t0,
        "error": None,
    }


# ---------------------------------------------------------------------
# Verdict computation (per ADR-108 §Operational + R1 C6)
# ---------------------------------------------------------------------


def compute_verdict(
    pass_1_results: List[Dict[str, Any]],
    pass_2_results: Optional[List[Dict[str, Any]]] = None,
    expected_n: int = TARGET_CORPUS_N,
) -> Dict[str, Any]:
    """Compute verdict per ADR-108 §Operational + R1 C6.

    Returns:
        {"verdict": str, "catch_rate_num": int, "catch_rate_den": int,
         "fp_count": int, "schema_adherence_num": int,
         "schema_adherence_den": int, "pass_2_used": bool,
         "manual_triage": bool}
    """
    den = len(pass_1_results)
    # "Catch" = verdict NOT in (TIMEOUT, MALFORMED) — Phase 4 stub
    # treats this as schema-adherence, NOT semantic catch-rate. Phase
    # 4-bis with real fixtures will refine: catch = (verdict matches
    # expected_verdict from MANIFEST).
    catch_num = sum(
        1 for r in pass_1_results
        if r.get("verdict") not in ("TIMEOUT", "MALFORMED")
    )
    schema_adherence_num = sum(
        1 for r in pass_1_results
        if r.get("verdict") not in ("MALFORMED",)
    )
    fp_count = 0  # Phase 4 stub; Phase 4-bis labels FPs

    # 2-pass logic
    pass_2_used = False
    if pass_2_results is not None:
        pass_2_used = True
        # Replace failed fixture's pass_1 result with pass_2
        if len(pass_2_results) == 1 and pass_2_results[0].get("verdict") not in ("TIMEOUT", "MALFORMED"):
            catch_num += 1  # rescued

    # Manual triage flag — partial corpus or Sec dissent path
    manual_triage = False
    if den < expected_n and os.environ.get("CEO_PHASE_4_PARTIAL_OK") != "1":
        manual_triage = True
    if den < expected_n and os.environ.get("CEO_PHASE_4_PARTIAL_OK") == "1":
        # Allowed via override but flagged as triage forensic
        manual_triage = True

    # Verdict dispatch
    if den == 0:
        verdict = "TRIAGE"
    elif catch_num == den and den == expected_n:
        if pass_2_used:
            verdict = "PASS_AFTER_RETRY"
        else:
            verdict = "PASS"
    elif catch_num == den - 1 and not pass_2_used:
        # Trigger Pass 2 (caller responsibility)
        verdict = "TRIAGE"
    elif catch_num >= den - 3:
        verdict = "TRIAGE"
        manual_triage = True
    else:
        verdict = "FAIL"
        manual_triage = True

    return {
        "verdict": verdict,
        "catch_rate_num": catch_num,
        "catch_rate_den": den,
        "fp_count": fp_count,
        "schema_adherence_num": schema_adherence_num,
        "schema_adherence_den": den,
        "pass_2_used": pass_2_used,
        "manual_triage": manual_triage,
    }


# ---------------------------------------------------------------------
# Routing-matrix flip (atomic temp+rename)
# ---------------------------------------------------------------------


def flip_routing_matrix(matrix_path: Path, dry_run: bool = True) -> bool:
    """Phase 4 ship: stub.

    Phase 4-bis wires real flip: edit routing-matrix.yaml entries
    where ``coder: claude`` (Phase 1 review-only) → ``coder: codex``
    (Phase 2 coder mode) for archetypes that passed the gate.
    Atomic write via tmp+rename. Returns True on flip; False on
    dry-run.

    Phase 4 ALWAYS no-ops because:
      1. Corpus is N=0 (Phase 4-bis authoring needed first).
      2. Phase 5 codando deny-list (`check_codex_filewrite.py`) must
         be live BEFORE Codex can act as coder.
      3. Owner must explicitly opt-in (env or sentinel).
    """
    if dry_run:
        return False
    # Phase 4 stub: never flip in this ship.
    return False


# ---------------------------------------------------------------------
# Filelock (per Codex iter 1 R-NEW-5)
# ---------------------------------------------------------------------


def acquire_promotion_lock(state_dir: Path) -> Optional[Any]:
    """Acquire filelock for promotion-gate run.

    Uses _lib/filelock.FileLock if available; falls back to a no-op
    on adopter installs without the lib. Returns the lock object
    (caller releases via context manager) or None if unavailable.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "pair-rail-promotion.lock"
    try:
        # Defer import; not all adopter installs have it on PYTHONPATH.
        hooks_dir = DEFAULT_REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.filelock import FileLock  # type: ignore
        lock = FileLock(str(lock_path))
        lock.acquire(timeout=10)
        return lock
    except Exception:
        return None


# ---------------------------------------------------------------------
# Audit emit (best-effort, fail-OPEN)
# ---------------------------------------------------------------------


def emit_promotion_verdict(
    *,
    run_id: str,
    verdict: str,
    corpus_n: int,
    corpus_manifest_sha: str,
    catch_rate_num: int,
    catch_rate_den: int,
    fp_rate_pct: float,
    schema_adherence_pct: float,
    rubric_gap_pp: float,
    codex_cli_version: str,
    git_head_sha: str,
    pass_2_retry_used: bool,
    manual_triage: bool,
) -> None:
    """Emit pair_rail_promotion. Best-effort; fail-OPEN."""

    def _bucket_fp(pct: float) -> str:
        if pct <= 15.0:
            return "<=15%"
        if pct <= 30.0:
            return "15-30%"
        return ">30%"

    def _bucket_schema(pct: float) -> str:
        if pct >= 100.0:
            return "100%"
        if pct >= 95.0:
            return "95-99%"
        return "<95%"

    def _bucket_rubric(pp: float) -> str:
        if pp <= 0.0:
            return "<=0pp"
        if pp <= 5.0:
            return "0-5pp"
        if pp <= 10.0:
            return "5-10pp"
        return ">10pp"

    try:
        hooks_dir = DEFAULT_REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        try:
            from _lib import audit_emit as _ae  # type: ignore
        except Exception:
            return
        if not hasattr(_ae, "emit_pair_rail_promotion"):
            return
        _ae.emit_pair_rail_promotion(
            run_id=run_id,
            verdict=verdict,
            corpus_n=corpus_n,
            corpus_manifest_sha=corpus_manifest_sha[:16],
            catch_rate_num=catch_rate_num,
            catch_rate_den=catch_rate_den,
            fp_rate_bucket=_bucket_fp(fp_rate_pct),
            schema_adherence_pct_bucket=_bucket_schema(schema_adherence_pct),
            rubric_gap_pp_bucket=_bucket_rubric(rubric_gap_pp),
            codex_cli_version=codex_cli_version,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            git_head_sha_prefix=git_head_sha[:12],
            pass_2_retry_used=pass_2_retry_used,
            manual_triage=manual_triage,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Pair-Rail promotion gate")
    parser.add_argument("--dry-run", action="store_true", help="No matrix flip")
    parser.add_argument("--parallel", type=int, default=1, help="Concurrent fixtures")
    args = parser.parse_args(argv)

    if os.environ.get("CEO_PHASE_AUTO_FLIP_DRY_RUN") == "1":
        args.dry_run = True

    repo_root = DEFAULT_REPO_ROOT
    state_dir = Path.home() / ".claude" / "projects" / repo_root.name / "state"
    run_id = uuid.uuid4().hex

    # Acquire lock (Codex iter 1 R-NEW-5)
    lock = acquire_promotion_lock(state_dir)

    try:
        # Pin git HEAD + corpus MANIFEST SHA at run start
        try:
            git_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True,
                cwd=str(repo_root), timeout=5,
            ).stdout.strip()
        except Exception:
            git_head = ""

        manifest_path = DEFAULT_MANIFEST_PATH
        try:
            manifest_sha = compute_sha256(manifest_path)
        except GateError:
            manifest_sha = ""

        # Warm-up Codex CLI (advisory)
        warmup_codex_cli()
        codex_v = get_codex_cli_version()

        # Parse + filter fixtures
        try:
            all_fixtures = parse_manifest(manifest_path)
        except GateError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1
        active = filter_active_fixtures(all_fixtures)

        # Pass 1
        pass_1_results = [
            review_fixture(f, repo_root, timeout_s=PASS_1_TIMEOUT_S)
            for f in active
        ]

        # Compute verdict
        verdict_data = compute_verdict(pass_1_results, expected_n=TARGET_CORPUS_N)

        # Pass 2 retry if catch_rate == N-1 with timeout/malformed
        pass_2_results = None
        if (
            verdict_data["verdict"] == "TRIAGE"
            and verdict_data["catch_rate_den"] == TARGET_CORPUS_N
            and verdict_data["catch_rate_num"] == TARGET_CORPUS_N - 1
        ):
            failed = [
                r for r in pass_1_results
                if r.get("verdict") in ("TIMEOUT", "MALFORMED")
            ]
            if len(failed) == 1:
                fixture_id = failed[0].get("fixture_id")
                fixture = next((f for f in active if f.get("id") == fixture_id), None)
                if fixture:
                    pass_2_results = [
                        review_fixture(fixture, repo_root, timeout_s=RETRY_TIMEOUT_S)
                    ]
                    verdict_data = compute_verdict(
                        pass_1_results, pass_2_results, expected_n=TARGET_CORPUS_N
                    )

        # Compute rates (Phase 4 stubs)
        fp_rate_pct = 0.0
        schema_pct = (
            (verdict_data["schema_adherence_num"] / verdict_data["schema_adherence_den"]) * 100
            if verdict_data["schema_adherence_den"] > 0 else 0.0
        )
        rubric_gap_pp = 0.0  # Phase 4-bis fixture authoring computes this

        # Audit emit
        emit_promotion_verdict(
            run_id=run_id,
            verdict=verdict_data["verdict"],
            corpus_n=len(active),
            corpus_manifest_sha=manifest_sha,
            catch_rate_num=verdict_data["catch_rate_num"],
            catch_rate_den=verdict_data["catch_rate_den"],
            fp_rate_pct=fp_rate_pct,
            schema_adherence_pct=schema_pct,
            rubric_gap_pp=rubric_gap_pp,
            codex_cli_version=codex_v,
            git_head_sha=git_head,
            pass_2_retry_used=verdict_data["pass_2_used"],
            manual_triage=verdict_data["manual_triage"],
        )

        # Auto-flip (stub at Phase 4)
        if verdict_data["verdict"] in ("PASS", "PASS_AFTER_RETRY") and not args.dry_run:
            flip_routing_matrix(DEFAULT_ROUTING_MATRIX, dry_run=False)

        # Print summary
        print(json.dumps({
            "run_id": run_id,
            "verdict": verdict_data["verdict"],
            "corpus_n": len(active),
            "catch_rate": f"{verdict_data['catch_rate_num']}/{verdict_data['catch_rate_den']}",
            "manual_triage": verdict_data["manual_triage"],
            "manifest_sha_prefix": manifest_sha[:16],
            "git_head_sha_prefix": git_head[:12],
            "codex_cli_version": codex_v,
            "dry_run": args.dry_run,
        }, indent=2))

        return 0 if verdict_data["verdict"] in ("PASS", "PASS_AFTER_RETRY") else 2
    finally:
        if lock is not None:
            try:
                lock.release()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
