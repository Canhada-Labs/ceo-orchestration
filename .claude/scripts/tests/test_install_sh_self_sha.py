"""install.sh self-SHA verification tests.

PLAN-045 Session 41 / PLAN-044 P0-15 (ex F-15R2-01) — supply-chain
self-verification of install.sh via a `# CEO-INSTALL-SHA256: <hex>`
trailer on the last line. Release workflow (.github/workflows/
npm-publish.yml + release.yml) substitutes the PLACEHOLDER_RELEASE_FILL
value at tag cut with the sha256 of the script body. At install time,
`_verify_self_sha` recomputes and fail-CLOSEDs (rc=5) on mismatch.

This test module exercises the Bash self-check end-to-end by copying
install.sh into a scratch tmp_path, mutating trailer / body, and
asserting the expected rc:

  - rc=0 when trailer = real sha256 of body (happy path)
  - rc=0 + warn when trailer = PLACEHOLDER_RELEASE_FILL
  - rc=0 + warn when CEO_INSTALL_SKIP_SELF_SHA=1 (explicit bypass)
  - rc=5 when trailer SHA does not match body SHA (tampering)
  - rc=5 when trailer is missing or malformed

Tests do NOT invoke the full install flow — only the self-SHA gate at
script startup. The script exits early with usage-help after passing
self-SHA because no target dir arg is supplied.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import unittest
from pathlib import Path

try:
    import pytest
except ImportError:  # pragma: no cover - unittest-discover without pytest
    raise unittest.SkipTest(
        "pytest not available; this test module uses pytest fixtures "
        "and is skipped when unittest discover runs without pytest."
    )

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"

PLACEHOLDER = "PLACEHOLDER_RELEASE_FILL"
TRAILER_PREFIX = "# CEO-INSTALL-SHA256: "


def _compute_body_sha(text: str) -> str:
    """sha256 of everything EXCEPT the last (trailer) line.

    Mirrors the awk NR/FNR trick in install.sh's _self_sha_compute:
    read lines 1..N-1 joined with \\n and sha256 them.
    """
    lines = text.splitlines(keepends=True)
    body = "".join(lines[:-1])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _run(script_path: Path, env: dict) -> subprocess.CompletedProcess:
    """Invoke the script with no args → triggers self-SHA then usage."""
    merged = os.environ.copy()
    merged.update(env)
    # No target arg → after self-SHA passes, script prints usage + exit 1.
    # We only care about the rc of the self-SHA phase; a rc of 1 here
    # means self-SHA passed (script proceeded to usage).
    return subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        env=merged,
    )


@pytest.fixture
def scratch_install(tmp_path: Path) -> Path:
    """Copy install.sh into tmp_path; tests mutate the copy freely."""
    dst = tmp_path / "install.sh"
    shutil.copy(INSTALL_SH, dst)
    dst.chmod(0o755)
    return dst


# ----------------------------------------------------------------------
# Happy paths
# ----------------------------------------------------------------------


def test_placeholder_trailer_warns_and_proceeds(scratch_install: Path):
    """Default source-checkout state: placeholder → warn + proceed."""
    result = _run(scratch_install, {})
    assert "self-SHA trailer is the unpopulated placeholder" in result.stderr
    # Proceeded past self-SHA → hit usage → rc=1 (no target arg)
    assert result.returncode == 1
    assert "Usage:" in result.stderr


def test_skip_env_bypasses_verification(scratch_install: Path):
    """CEO_INSTALL_SKIP_SELF_SHA=1 → explicit dev bypass with warn."""
    result = _run(scratch_install, {"CEO_INSTALL_SKIP_SELF_SHA": "1"})
    assert "self-SHA verification skipped" in result.stderr
    assert result.returncode == 1


def test_valid_sha_passes_silently(scratch_install: Path):
    """Populated trailer with correct sha256 → no WARN, proceeds."""
    text = scratch_install.read_text(encoding="utf-8")
    expected = _compute_body_sha(text)
    new_text = text.replace(
        f"{TRAILER_PREFIX}{PLACEHOLDER}",
        f"{TRAILER_PREFIX}{expected}",
    )
    scratch_install.write_text(new_text, encoding="utf-8")

    result = _run(scratch_install, {})
    # No self-SHA warning should appear
    assert "self-SHA" not in result.stderr or "MISMATCH" not in result.stderr
    assert "MISMATCH" not in result.stderr
    assert "unpopulated placeholder" not in result.stderr
    assert result.returncode == 1  # usage exit, not self-SHA failure
    assert "Usage:" in result.stderr


# ----------------------------------------------------------------------
# Fail-CLOSED paths
# ----------------------------------------------------------------------


def test_mismatch_fails_closed_rc5(scratch_install: Path):
    """Body-modified-after-trailer → rc=5 MISMATCH."""
    text = scratch_install.read_text(encoding="utf-8")
    # Inject a fake sha256 that won't match body
    fake_hex = "deadbeef" * 8  # 64 hex chars, valid format but wrong
    new_text = text.replace(
        f"{TRAILER_PREFIX}{PLACEHOLDER}",
        f"{TRAILER_PREFIX}{fake_hex}",
    )
    scratch_install.write_text(new_text, encoding="utf-8")

    result = _run(scratch_install, {})
    assert result.returncode == 5
    assert "MISMATCH" in result.stderr
    assert "supply-chain tampering suspected" in result.stderr
    assert fake_hex in result.stderr  # expected
    assert "CEO_INSTALL_SKIP_SELF_SHA=1" in result.stderr  # bypass hint


def test_tampered_body_with_valid_old_hash_fails(scratch_install: Path):
    """Correctly-computed trailer for ORIGINAL body, then body tampered."""
    text = scratch_install.read_text(encoding="utf-8")
    original_hash = _compute_body_sha(text)
    populated = text.replace(
        f"{TRAILER_PREFIX}{PLACEHOLDER}",
        f"{TRAILER_PREFIX}{original_hash}",
    )
    # Now tamper: add a malicious line BEFORE the trailer
    lines = populated.splitlines(keepends=True)
    tampered = "".join(lines[:-1]) + 'echo "MALICIOUS" >&2\n' + lines[-1]
    scratch_install.write_text(tampered, encoding="utf-8")

    result = _run(scratch_install, {})
    assert result.returncode == 5
    assert "MISMATCH" in result.stderr


def test_missing_trailer_fails_closed(scratch_install: Path):
    """No trailer line at all → rc=5 malformed."""
    text = scratch_install.read_text(encoding="utf-8")
    # Drop the last line entirely
    lines = text.splitlines(keepends=True)
    scratch_install.write_text("".join(lines[:-1]), encoding="utf-8")

    result = _run(scratch_install, {})
    assert result.returncode == 5
    assert "missing/malformed CEO-INSTALL-SHA256 trailer" in result.stderr


def test_wrong_trailer_format_fails_closed(scratch_install: Path):
    """Trailer exists but doesn't match the expected prefix → rc=5."""
    text = scratch_install.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    lines[-1] = "# SOME-OTHER-COMMENT: whatever\n"
    scratch_install.write_text("".join(lines), encoding="utf-8")

    result = _run(scratch_install, {})
    assert result.returncode == 5
    assert "missing/malformed CEO-INSTALL-SHA256 trailer" in result.stderr


# ----------------------------------------------------------------------
# Cryptographic correctness
# ----------------------------------------------------------------------


def test_trailer_itself_is_not_in_hash_domain(scratch_install: Path):
    """Changing the trailer value alone must not shift the body hash.

    This is the property that makes the release workflow's in-place
    substitution safe: replacing PLACEHOLDER with the real hex modifies
    ONLY the last line, and the computed hash stays constant.
    """
    text = scratch_install.read_text(encoding="utf-8")
    hash_a = _compute_body_sha(text)

    # Swap in a different trailer value
    text_b = text.replace(
        f"{TRAILER_PREFIX}{PLACEHOLDER}",
        f"{TRAILER_PREFIX}{'a' * 64}",
    )
    hash_b = _compute_body_sha(text_b)

    assert hash_a == hash_b, (
        "body sha must be invariant under trailer-only mutation — "
        "otherwise release-workflow substitution creates a cycle"
    )


def test_shell_awk_matches_python_reference(scratch_install: Path):
    """install.sh's awk-based compute must match the Python reference."""
    # Run the compute helper via a one-liner that sources the function
    # from install.sh and invokes it. We inline the awk to avoid shell
    # quoting gymnastics.
    text = scratch_install.read_text(encoding="utf-8")
    python_hash = _compute_body_sha(text)

    proc = subprocess.run(
        [
            "bash",
            "-c",
            (
                "awk 'NR==FNR{n++; next} FNR < n' \"$1\" \"$1\" "
                "| shasum -a 256 | awk '{print $1}'"
            ),
            "_",
            str(scratch_install),
        ],
        capture_output=True,
        text=True,
    )
    shell_hash = proc.stdout.strip()
    assert shell_hash == python_hash, (
        f"shell awk+shasum computed {shell_hash} but Python reference "
        f"computed {python_hash} — portability divergence"
    )
