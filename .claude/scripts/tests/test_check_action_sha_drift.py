"""Tests for `.claude/scripts/check-action-sha-drift.py`.

Focus: PLAN-050 Phase 6 (C12) format-compliance hard-fail contract +
PLAN-153 Wave E item 4 workflow-policy assertions (`--policy`).

Tagging claim drift (advisory) relies on live GitHub API calls which
we don't exercise in unit tests (flaky, rate-limited). The `--offline`
flag is tested to confirm the network path is bypassed cleanly.

The PolicyAssertionTests below are behavioral positive-controls in the
Wave E sense: each planted violation is a known-bad INPUT the validator
MUST red (exit 1). All workflow snippets are inert test DATA written to
a TemporaryDirectory — they are never executed by any CI runner.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
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


_GOOD_SHA = "abcdef0123456789abcdef0123456789abcdef01"


class PolicyAssertionTests(unittest.TestCase):
    """PLAN-153 Wave E item 4 — `--policy` workflow-policy assertions.

    Positive controls: planted violations MUST exit 1. Negative
    controls: comment-only mentions, guarded secrets, GITHUB_TOKEN,
    and non-fork-reachable triggers MUST stay green.
    """

    def _run(self, files, policy: bool = True) -> int:
        """files: {name: str-content | bytes-content} (inert DATA)."""
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            for name, content in files.items():
                p = wf_dir / name
                if isinstance(content, bytes):
                    p.write_bytes(content)
                else:
                    p.write_text(content, encoding="utf-8")
            mod = _load_module()
            argv = ["--workflows-dir", str(wf_dir), "--offline"]
            if policy:
                argv.append("--policy")
            return mod.main(argv)

    # --- pull_request_target (forbidden trigger) ---

    def test_prt_key_trigger_blocked(self) -> None:
        # POSITIVE CONTROL — planted forbidden trigger must red.
        content = (
            "on:\n  pull_request_target:\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"prt.yml": content}), 1)

    def test_prt_inline_list_blocked(self) -> None:
        content = (
            "on: [push, pull_request_target]\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"prt.yml": content}), 1)

    def test_prt_scalar_on_blocked(self) -> None:
        content = (
            "on: pull_request_target\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"prt.yml": content}), 1)

    def test_prt_block_list_item_blocked(self) -> None:
        content = (
            "on:\n  - push\n  - pull_request_target\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"prt.yml": content}), 1)

    def test_prt_comment_only_passes(self) -> None:
        # NEGATIVE CONTROL — the repo's own workflows mention the
        # forbidden trigger in prose comments (e.g. tournament.yml:11).
        content = (
            "# pull_request_target EXPLICITLY FORBIDDEN per PLAN-002\n"
            "on:\n  push:  # never pull_request_target here\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}  # v4\n"
        )
        self.assertEqual(self._run({"ok.yml": content}), 0)

    def test_prt_with_head_checkout_message_aggravated(self) -> None:
        content = (
            "on:\n  pull_request_target:\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
            "        with:\n"
            "          ref: ${{ github.event.pull_request.head.sha }}\n"
        )
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "prt.yml").write_text(content, encoding="utf-8")
            mod = _load_module()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = mod.main(
                    ["--workflows-dir", str(wf_dir), "--offline", "--policy"]
                )
        self.assertEqual(code, 1)
        self.assertIn("RCE-equivalent", err.getvalue())

    # --- fork-reachable secrets ---

    def test_unguarded_secret_in_pr_workflow_blocked(self) -> None:
        # POSITIVE CONTROL — secret reachable from a fork PR, no guard.
        content = (
            "on:\n  pull_request:\n"
            "jobs:\n  job:\n"
            "    env:\n"
            "      API_KEY: ${{ secrets.PROVIDER_KEY }}\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"leak.yml": content}), 1)

    def test_guarded_secret_in_pr_workflow_passes(self) -> None:
        # NEGATIVE CONTROL — benchmarks.yml shape (_README.md §R9).
        content = (
            "on:\n  pull_request:\n"
            "jobs:\n  job:\n"
            "    if: github.event.pull_request.head.repo.full_name == github.repository\n"
            "    env:\n"
            "      API_KEY: ${{ secrets.PROVIDER_KEY }}\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"guarded.yml": content}), 0)

    def test_github_token_only_passes(self) -> None:
        # GITHUB_TOKEN is read-only for fork PRs — excluded by design.
        content = (
            "on:\n  pull_request:\n"
            "jobs:\n  job:\n"
            "    env:\n"
            "      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"token.yml": content}), 0)

    def test_push_only_secret_passes(self) -> None:
        # Not fork-reachable: push/schedule-only workflows may consume
        # secrets without a head-repo guard.
        content = (
            "on:\n  push:\n    branches: [main]\n"
            "jobs:\n  job:\n"
            "    env:\n"
            "      API_KEY: ${{ secrets.PROVIDER_KEY }}\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"push.yml": content}), 0)

    def test_prose_secrets_path_not_flagged(self) -> None:
        # `check_output_secrets.py` in a run command is prose, not an
        # expression — must not count as a secret reference (the
        # coverage.yml false-positive class).
        content = (
            "on:\n  pull_request:\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
            "      - run: python3 check_output_secrets.py --tier1\n"
        )
        self.assertEqual(self._run({"prose.yml": content}), 0)

    # --- fail-closed on unparseable input (PLAN-152 C4 precedent) ---

    def test_undecodable_file_fails_closed_under_policy(self) -> None:
        # POSITIVE CONTROL — input the matcher cannot parse is blocked.
        bad = b"\xff\xfe\x00\x00 not utf-8 \xff"
        self.assertEqual(self._run({"bad.yml": bad}), 1)

    def test_undecodable_file_skipped_without_policy(self) -> None:
        # Documents the historical pin-scan behavior (skip-on-unreadable)
        # so the asymmetry with --policy is explicit and frozen.
        bad = b"\xff\xfe\x00\x00 not utf-8 \xff"
        self.assertEqual(self._run({"bad.yml": bad}, policy=False), 0)

    # --- back-compat ---

    def test_policy_off_by_default(self) -> None:
        # Without --policy, a planted pull_request_target is NOT flagged
        # — existing CI invocations (validate.yml --offline) unchanged.
        content = (
            "on:\n  pull_request_target:\n"
            "jobs:\n  job:\n    steps:\n"
            f"      - uses: actions/checkout@{_GOOD_SHA}\n"
        )
        self.assertEqual(self._run({"prt.yml": content}, policy=False), 0)

    def test_policy_and_format_violations_both_reported(self) -> None:
        content = (
            "on:\n  pull_request_target:\n"
            "jobs:\n  job:\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        with TemporaryDirectory() as td:
            wf_dir = Path(td) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "both.yml").write_text(content, encoding="utf-8")
            mod = _load_module()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = mod.main(
                    ["--workflows-dir", str(wf_dir), "--offline", "--policy"]
                )
        self.assertEqual(code, 1)
        output = err.getvalue()
        self.assertIn("FORMAT VIOLATIONS", output)
        self.assertIn("POLICY VIOLATIONS", output)

    # --- the repo's own workflows are the live negative control ---

    def test_real_repo_workflows_policy_clean(self) -> None:
        """The actual .github/workflows tree must stay policy-clean.

        This is the regression gate: if a future workflow introduces
        pull_request_target or an unguarded fork-reachable secret, this
        test reds locally and in CI before the weekly watch does.
        """
        real_dir = (
            Path(__file__).resolve().parents[3] / ".github" / "workflows"
        )
        if not real_dir.is_dir():
            self.skipTest("repo workflows dir not present in this context")
        mod = _load_module()
        code = mod.main(
            ["--workflows-dir", str(real_dir), "--offline", "--policy"]
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
