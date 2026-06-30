"""Tests for `.claude/scripts/check-action-sha-drift.py`.

Focus: PLAN-050 Phase 6 (C12) format-compliance hard-fail contract.

Tagging claim drift (advisory) relies on live GitHub API calls which
we don't exercise in unit tests (flaky, rate-limited). The `--offline`
flag is tested to confirm the network path is bypassed cleanly.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_SCRIPT = Path(__file__).resolve().parents[1] / "check-action-sha-drift.py"


def _load_module():
    """Load the hyphenated script as a Python module for direct call."""
    spec = importlib.util.spec_from_file_location("check_action_sha_drift", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FormatComplianceTests(unittest.TestCase):
    """PLAN-050 C12 — non-SHA pins trigger exit code 1."""

    def _run(self, workflow_content: str, argv_extra=None) -> int:
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "test.yml").write_text(workflow_content, encoding="utf-8")
            mod = _load_module()
            argv = ["--workflows-dir", str(wf_dir), "--offline"]
            if argv_extra:
                argv.extend(argv_extra)
            return mod.main(argv)

    def test_valid_sha_pin_passes(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/checkout@abcdef0123456789abcdef0123456789abcdef01\n"
        self.assertEqual(self._run(content), 0)

    def test_tag_pin_fails(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/checkout@v4\n"
        self.assertEqual(self._run(content), 1)

    def test_branch_pin_fails(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/setup-python@main\n"
        self.assertEqual(self._run(content), 1)

    def test_short_sha_fails(self) -> None:
        # 7-char abbreviated SHA is not allowed
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/checkout@abcdef0\n"
        self.assertEqual(self._run(content), 1)

    def test_multiple_pins_one_violation_fails(self) -> None:
        content = (
            "jobs:\n  job:\n    steps:\n"
            "      - uses: actions/checkout@abcdef0123456789abcdef0123456789abcdef01\n"
            "      - uses: actions/setup-python@v5\n"
        )
        self.assertEqual(self._run(content), 1)

    def test_sha_with_tag_comment_passes(self) -> None:
        content = (
            "jobs:\n  job:\n    steps:\n"
            "      - uses: actions/checkout@abcdef0123456789abcdef0123456789abcdef01  # v4\n"
        )
        self.assertEqual(self._run(content), 0)

    def test_local_action_exempt(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: ./local-action\n"
        self.assertEqual(self._run(content), 0)

    def test_docker_action_exempt(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: docker://alpine:3.18\n"
        self.assertEqual(self._run(content), 0)

    def test_commented_line_ignored(self) -> None:
        content = (
            "jobs:\n  job:\n    steps:\n"
            "      # - uses: actions/checkout@v4\n"
            "      - uses: actions/checkout@abcdef0123456789abcdef0123456789abcdef01\n"
        )
        self.assertEqual(self._run(content), 0)

    def test_uppercase_sha_accepted(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/checkout@ABCDEF0123456789ABCDEF0123456789ABCDEF01\n"
        self.assertEqual(self._run(content), 0)

    def test_subpath_action_accepted(self) -> None:
        content = "jobs:\n  job:\n    steps:\n      - uses: actions/cache/save@abcdef0123456789abcdef0123456789abcdef01\n"
        self.assertEqual(self._run(content), 0)

    def test_empty_dir_noop(self) -> None:
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / "empty"
            wf_dir.mkdir()
            mod = _load_module()
            code = mod.main(["--workflows-dir", str(wf_dir), "--offline"])
            self.assertEqual(code, 0)

    def test_nonexistent_dir_noop(self) -> None:
        mod = _load_module()
        code = mod.main([
            "--workflows-dir", "/nonexistent/path/ever",
            "--offline",
        ])
        # Nonexistent dir is treated as no-files → exit 0 (no-op).
        self.assertEqual(code, 0)

    def test_yaml_extension_scanned(self) -> None:
        # Files with .yaml extension (not .yml) must also be scanned.
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "test.yaml").write_text(
                "jobs:\n  job:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            mod = _load_module()
            code = mod.main(["--workflows-dir", str(wf_dir), "--offline"])
            self.assertEqual(code, 1)


class SSLContextTests(unittest.TestCase):
    """PLAN-050 C12 — strict TLS."""

    def test_build_ssl_context_hostname_check_enabled(self) -> None:
        mod = _load_module()
        ctx = mod._build_ssl_context()
        self.assertTrue(ctx.check_hostname)

    def test_build_ssl_context_cert_required(self) -> None:
        mod = _load_module()
        ctx = mod._build_ssl_context()
        import ssl
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)


class GitHubHeadersTests(unittest.TestCase):
    """PLAN-050 C12 — GITHUB_TOKEN auth."""

    def test_no_token_no_auth_header(self) -> None:
        mod = _load_module()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            headers = mod._github_headers()
            self.assertNotIn("Authorization", headers)
            self.assertEqual(
                headers["User-Agent"], "ceo-orchestration-sha-drift-check"
            )

    def test_token_present_bearer_auth(self) -> None:
        mod = _load_module()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghs_testtoken123"}):
            headers = mod._github_headers()
            self.assertEqual(headers["Authorization"], "Bearer ghs_testtoken123")

    def test_empty_token_treated_as_absent(self) -> None:
        mod = _load_module()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "  "}):
            headers = mod._github_headers()
            self.assertNotIn("Authorization", headers)


if __name__ == "__main__":
    unittest.main()
