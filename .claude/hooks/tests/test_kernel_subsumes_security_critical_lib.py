"""PLAN-085 Wave E.2 — _KERNEL_PATHS subsumption tests.

13 parametrized cases (one per ADR-116 added entry) asserting each new
kernel-protected path is detected by `_is_kernel_path` after Wave E.2.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from check_arbitration_kernel import _KERNEL_PATHS, _is_kernel_path  # noqa: E402


# Each tuple: (logical_label, path_to_test, expected_kernel_match).
ADR_116_NEW_PATHS = [
    ("settings_json", ".claude/settings.json", True),
    ("python_hook_sh", ".claude/hooks/_python-hook.sh", True),
    ("gpg_verify", ".claude/hooks/_lib/gpg_verify.py", True),
    ("audit_hmac", ".claude/hooks/_lib/audit_hmac.py", True),
    ("secret_patterns", ".claude/hooks/_lib/secret_patterns.py", True),
    ("injection_patterns", ".claude/hooks/_lib/injection_patterns.py", True),
    ("output_scan", ".claude/hooks/_lib/output_scan.py", True),
    ("codex_egress_redact", ".claude/hooks/_lib/codex_egress_redact.py", True),
    ("dispatcher_yaml", ".claude/dispatcher/routing-matrix.yaml", True),
    ("dispatcher_py", ".claude/dispatcher/routing-matrix-loader.py", True),
    ("release_workflow", ".github/workflows/release.yml", True),
    ("validate_workflow", ".github/workflows/validate.yml", True),
    ("sentinel_signers", ".claude/sentinel-signers.txt", True),
    ("trusted_env", ".claude/hooks/_lib/trusted_env.py", True),
]

# Negative controls — these paths MUST NOT match any kernel pattern.
NEGATIVE_CONTROLS = [
    "README.md",
    "scripts/install.sh",
    ".claude/plans/PLAN-001-evolution.md",
    "tests/test_codex_redact_fail_closed.py",
    ".claude/adr/ADR-120-pii-core-promotion.md",  # ADR is sentinel-only, NOT kernel
]


class TestKernelSubsumesSecurityCriticalLib(unittest.TestCase):
    """ADR-116 13-entry kernel extension parametrized subsumption tests."""

    def test_kernel_paths_count_at_least_27(self) -> None:
        """Pre-extension was 14 entries; ADR-116 adds 13."""
        self.assertGreaterEqual(
            len(_KERNEL_PATHS),
            27,
            msg=f"_KERNEL_PATHS count is {len(_KERNEL_PATHS)}; expected >= 27 post-E.2",
        )

    def test_each_adr116_entry_matches_kernel(self) -> None:
        """Each ADR-116 added path resolves to kernel-tier via _is_kernel_path."""
        for label, path_str, expected in ADR_116_NEW_PATHS:
            with self.subTest(label=label, path=path_str):
                # Construct an absolute path under the repo root for fnmatch
                abs_path = REPO_ROOT / path_str
                result = _is_kernel_path(str(abs_path), REPO_ROOT)
                self.assertEqual(
                    result,
                    expected,
                    msg=(
                        f"ADR-116 entry {label!r} (path={path_str}) "
                        f"kernel-match={result}, expected={expected}"
                    ),
                )

    def test_negative_controls_not_kernel(self) -> None:
        """Non-kernel paths MUST NOT match the extended _KERNEL_PATHS list."""
        for path_str in NEGATIVE_CONTROLS:
            with self.subTest(path=path_str):
                abs_path = REPO_ROOT / path_str
                self.assertFalse(
                    _is_kernel_path(str(abs_path), REPO_ROOT),
                    msg=f"unexpected kernel-match for {path_str!r}",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
