"""test_validate_pair_rail_verdict.py — S104 PLAN-081 GA tail.

Tests for the parent_sha / commit_sha bind redesign in
.github/scripts/validate-pair-rail-verdict.py. The legacy
`verdict.commit_sha` self-reference is replaced with `verdict.parent_sha`
to break the chicken-and-egg problem the v1.16.0 GA ceremony hit
(verdict file cannot declare its own commit SHA because the SHA is
only known AFTER the verdict file is committed).

Coverage:
- --parent-sha match → exit 0
- --parent-sha mismatch → exit VERDICT_INVALID (3)
- --parent-sha against verdict with no parent_sha field, legacy
  commit_sha present → ADVISORY (skip bind), exit 0 if rest valid
- --parent-sha against verdict with no parent_sha + no commit_sha →
  exit VERDICT_INVALID (3)
- Legacy --commit-sha path still works on legacy verdicts (exit 0)
- Legacy --commit-sha mismatch → exit VERDICT_INVALID (3)
- --parent-sha takes precedence when both args passed

ADR-182 payload pin (PLAN-163 T5.2 pin-pack):
- --codex-pin-manifest-file + matching triple/sha envelope → exit 0
- payload sha mismatch → VERDICT_INVALID (3)
- targetTriple absent from manifest → VERDICT_INVALID (3)
- envelope missing triple/sha fields → VERDICT_INVALID (3)
- manifest file unreadable → infra (1)
- comment-only tombstone as --codex-cli-binary-sha256-file → legacy
  launcher pin skipped (exit 0)

Stdlib only. Python ≥3.9. Run via pytest from repo root.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "validate-pair-rail-verdict.py"

EXIT_OK = 0
EXIT_INFRA_ERROR = 1
EXIT_VERDICT_EXPIRED = 2
EXIT_VERDICT_INVALID = 3


def _make_verdict(
    *,
    decision_lines: Sequence[str] = ("verdict: GO",),
    release_tag: str = "v1.99.0",
    parent_sha: str = "",
    commit_sha: str = "",
    inputs_hash: str = "deadbeef" * 8,
    generated_at: str = "9999-01-01T00:00:00Z",
    ttl_hours: int = 87600,
    tool_versions_block: str = (
        "  codex_cli: 0.129.0\n"
        "  codex_cli_binary_sha256: " + "a" * 64
    ),
    include_signature: bool = True,
) -> str:
    """Build a verdict markdown file with the requested envelope.

    `decision_lines` are emitted VERBATIM (PLAN-177 t2 / P1-a): the grammar
    divergence between this validator and the local tag guard can only be
    expressed by writing the key spelling itself -- `verdict : NO-GO` is
    valid YAML and was counted here but skipped there.
    """
    lines = [
        "# Pair-Rail Verdict — test",
        "",
        "```yaml",
        *decision_lines,
        f"generated_at: {generated_at}",
        f"ttl_hours: {ttl_hours}",
        f"release_tag: {release_tag}",
    ]
    if parent_sha:
        lines.append(f"parent_sha: {parent_sha}")
    if commit_sha:
        lines.append(f"commit_sha: {commit_sha}")
    lines.append(f"inputs_hash: {inputs_hash}")
    lines.append("tool_versions:")
    lines.append(tool_versions_block)
    if include_signature:
        lines.append("gpg_signature: |")
        lines.append("  -----BEGIN PGP SIGNATURE-----")
        lines.append("  fake-sig-for-test")
        lines.append("  -----END PGP SIGNATURE-----")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _run(args, verdict_text: str):
    """Run validator on a tmpdir-scoped verdict file. Returns CompletedProcess."""
    with tempfile.TemporaryDirectory() as td:
        verdict_path = Path(td) / "verdict.md"
        verdict_path.write_text(verdict_text, encoding="utf-8")
        cmd = [
            sys.executable, str(SCRIPT),
            "--verdict-file", str(verdict_path),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


class TestParentShaBind(unittest.TestCase):
    """S104 redesign: --parent-sha is the canonical bind."""

    PARENT = "abcdef0123456789abcdef0123456789abcdef01"

    def test_parent_sha_match_passes_bind(self):
        v = _make_verdict(parent_sha=self.PARENT, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        # Bind passes; other checks may still pass too (no pin files
        # requested → skipped). Expected exit 0.
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)

    def test_parent_sha_mismatch_returns_invalid(self):
        v = _make_verdict(parent_sha=self.PARENT, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", "f" * 40,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("parent_sha mismatch", r.stderr)

    def test_parent_sha_arg_with_legacy_commit_sha_only_advises(self):
        """v1.16.0-era verdict shipping commit_sha but not parent_sha,
        invoked with --parent-sha → ADVISORY skip, proceed."""
        v = _make_verdict(commit_sha="deadbeef" * 5, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)
        self.assertIn("ADVISORY", r.stderr)
        self.assertIn("legacy commit_sha", r.stderr)

    def test_parent_sha_arg_with_no_sha_fields_returns_invalid(self):
        v = _make_verdict(release_tag="v1.99.0")  # neither parent_sha nor commit_sha
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("missing parent_sha field", r.stderr)


class TestNonCanonicalTopLevelKeySyntax(unittest.TestCase):
    """PLAN-177 t2 (re-pass rc.4 P1-a) — one grammar for both release rails.

    `verdict : NO-GO` is valid YAML and last-wins under a real parser. THIS
    validator strips the key, so it saw two declarations; the local tag guard
    (`.claude/scripts/local/_release_tag_guard.py`, the rail with no escape
    hatch) required the colon immediately after the name, saw ONE, and parsed
    the following `verdict: GO`. Cured semantics, identical in both files:
    non-canonical top-level syntax is REFUSED — exit 3, never 1, so the
    transition mode cannot wave it through.
    """

    PARENT = "abcdef0123456789abcdef0123456789abcdef01"
    DIAGNOSTIC = "non-canonical top-level key syntax"

    def _run_decisions(self, decision_lines):
        v = _make_verdict(
            decision_lines=decision_lines,
            parent_sha=self.PARENT,
            release_tag="v1.99.0",
        )
        return _run(
            ["--parent-sha", self.PARENT, "--release-tag", "v1.99.0"], v
        )

    def test_space_before_colon_duplicate_is_refused(self):
        r = self._run_decisions(["verdict : NO-GO", "verdict: GO"])
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID, msg=r.stderr)
        self.assertIn(self.DIAGNOSTIC, r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_tab_before_colon_duplicate_is_refused(self):
        r = self._run_decisions(["verdict\t: NO-GO", "verdict: GO"])
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID, msg=r.stderr)
        self.assertIn(self.DIAGNOSTIC, r.stderr)

    def test_single_noncanonical_key_is_refused(self):
        """Not only the duplicate shape: a lone `verdict : GO` is a spelling
        the two readers disagree about, so it is refused rather than read."""
        for line in ("verdict : GO", "verdict\t: GO"):
            r = self._run_decisions([line])
            self.assertEqual(r.returncode, EXIT_VERDICT_INVALID, msg=r.stderr)
            self.assertIn(self.DIAGNOSTIC, r.stderr)
            self.assertNotEqual(r.returncode, EXIT_INFRA_ERROR)

    def test_canonical_envelope_is_untouched_by_the_shape_gate(self):
        """The control that keeps the gate from being a blanket refusal."""
        r = self._run_decisions(["verdict: GO"])
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)
        self.assertNotIn(self.DIAGNOSTIC, r.stderr)

    def test_list_items_and_sub_keys_stay_canonical(self):
        """delta_allowlist entries and `tool_versions:` children are the two
        non-`name:` shapes a real envelope carries — neither may trip it."""
        v = _make_verdict(
            decision_lines=[
                "verdict: GO",
                "delta_allowlist:",
                "  - .claude/governance/pair-rail-verdict-v1.99.0.md",
            ],
            parent_sha=self.PARENT,
            release_tag="v1.99.0",
        )
        r = _run(
            ["--parent-sha", self.PARENT, "--release-tag", "v1.99.0"], v
        )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)
        self.assertNotIn(self.DIAGNOSTIC, r.stderr)


class TestLegacyCommitShaBind(unittest.TestCase):
    """Backward-compat with v1.16.0-era release.yml invocations."""

    COMMIT = "1234567890abcdef1234567890abcdef12345678"

    def test_legacy_commit_sha_match_passes(self):
        v = _make_verdict(commit_sha=self.COMMIT, release_tag="v1.16.0")
        r = _run(
            [
                "--commit-sha", self.COMMIT,
                "--release-tag", "v1.16.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)

    def test_legacy_commit_sha_mismatch_returns_invalid(self):
        v = _make_verdict(commit_sha=self.COMMIT, release_tag="v1.16.0")
        r = _run(
            [
                "--commit-sha", "f" * 40,
                "--release-tag", "v1.16.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("commit_sha mismatch", r.stderr)


class TestPrecedenceParentOverCommit(unittest.TestCase):
    """When both --parent-sha + --commit-sha passed, --parent-sha wins."""

    def test_parent_sha_wins_when_both_passed(self):
        # Verdict has both fields; mismatch the commit_sha but match parent_sha.
        # Validator should accept based on parent_sha (precedence).
        parent = "a" * 40
        commit = "b" * 40
        v = _make_verdict(
            parent_sha=parent, commit_sha=commit, release_tag="v1.99.0"
        )
        r = _run(
            [
                "--parent-sha", parent,
                "--commit-sha", "f" * 40,  # would FAIL legacy bind
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        # parent_sha matches → bind passes. commit_sha arg ignored.
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)


class TestReleaseTagReplayDefense(unittest.TestCase):
    """R1 S-Sec-3: release_tag bind survives the redesign."""

    def test_release_tag_mismatch_returns_invalid(self):
        v = _make_verdict(parent_sha="a" * 40, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", "a" * 40,
                "--release-tag", "v1.99.0-rc.1",  # different tag
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("release_tag mismatch", r.stderr)


# ---------------------------------------------------------------------
# ADR-182 payload pin (PLAN-163 T5.2 pin-pack)
# ---------------------------------------------------------------------

_TRIPLE = "aarch64-apple-darwin"
_PAYLOAD_SHA = "80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff"


def _adr182_tool_versions(
    *, triple: str = _TRIPLE, payload_sha: str = _PAYLOAD_SHA
) -> str:
    return (
        "  codex_cli: 0.129.0\n"
        f"  codex_target_triple: {triple}\n"
        f"  codex_payload_sha256: {payload_sha}"
    )


def _manifest_json(
    *, triple: str = _TRIPLE, payload_sha: str = _PAYLOAD_SHA
) -> str:
    import json as _json
    return _json.dumps(
        {
            "schema": 1,
            "package_version": "0.144.6",
            "npm_integrity": "sha512-test-only",
            "payloads": {
                triple: {
                    "path": (
                        "@openai/codex-darwin-arm64/vendor/"
                        + triple + "/bin/codex"
                    ),
                    "sha256": payload_sha,
                }
            },
        }
    )


def _run_with_manifest(args, verdict_text: str, manifest_text):
    """Run validator with a tmpdir-scoped verdict + manifest pair.

    ``manifest_text`` None → pass a nonexistent manifest path (the
    infra arm).
    """
    with tempfile.TemporaryDirectory() as td:
        verdict_path = Path(td) / "verdict.md"
        verdict_path.write_text(verdict_text, encoding="utf-8")
        manifest_path = Path(td) / "codex-cli-pin-manifest.json"
        if manifest_text is not None:
            manifest_path.write_text(manifest_text, encoding="utf-8")
        cmd = [
            sys.executable, str(SCRIPT),
            "--verdict-file", str(verdict_path),
            "--codex-pin-manifest-file", str(manifest_path),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


class TestAdr182PayloadPin(unittest.TestCase):
    """--codex-pin-manifest-file: fail-CLOSED payload-pin enforcement."""

    BASE_ARGS = ["--parent-sha", "a" * 40, "--release-tag", "v1.99.0"]

    def _verdict(self, tool_versions_block: str) -> str:
        return _make_verdict(
            parent_sha="a" * 40,
            release_tag="v1.99.0",
            tool_versions_block=tool_versions_block,
        )

    def test_matching_triple_and_sha_passes(self):
        v = self._verdict(_adr182_tool_versions())
        r = _run_with_manifest(self.BASE_ARGS, v, _manifest_json())
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)

    def test_payload_sha_mismatch_returns_invalid(self):
        v = self._verdict(_adr182_tool_versions(payload_sha="f" * 64))
        r = _run_with_manifest(self.BASE_ARGS, v, _manifest_json())
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("codex_payload_sha256 mismatch", r.stderr)

    def test_triple_absent_from_manifest_returns_invalid(self):
        v = self._verdict(
            _adr182_tool_versions(triple="x86_64-unknown-linux-musl")
        )
        r = _run_with_manifest(self.BASE_ARGS, v, _manifest_json())
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("absent from", r.stderr)

    def test_envelope_missing_pin_fields_returns_invalid(self):
        # Old-style envelope (launcher sha only, no triple/payload sha)
        v = self._verdict(
            "  codex_cli: 0.129.0\n"
            "  codex_cli_binary_sha256: " + "a" * 64
        )
        r = _run_with_manifest(self.BASE_ARGS, v, _manifest_json())
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("lacks tool_versions.codex_target_triple", r.stderr)

    def test_manifest_unreadable_is_infra(self):
        v = self._verdict(_adr182_tool_versions())
        r = _run_with_manifest(self.BASE_ARGS, v, None)
        self.assertEqual(r.returncode, EXIT_INFRA_ERROR)
        self.assertIn("INFRA", r.stderr)

    def test_manifest_bad_schema_returns_invalid(self):
        v = self._verdict(_adr182_tool_versions())
        r = _run_with_manifest(self.BASE_ARGS, v, '{"schema": 2}')
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("schema violation", r.stderr)


class TestLegacyLauncherPinTombstone(unittest.TestCase):
    """The retired codex-cli-binary-sha256.txt is comment-only; the
    legacy --codex-cli-binary-sha256-file path must treat it as "no
    launcher pin" and skip (ADR-182 tombstone semantics)."""

    def test_comment_only_pin_file_skips_legacy_check(self):
        v = _make_verdict(
            parent_sha="a" * 40,
            release_tag="v1.99.0",
            tool_versions_block="  codex_cli: 0.129.0",
        )
        with tempfile.TemporaryDirectory() as td:
            verdict_path = Path(td) / "verdict.md"
            verdict_path.write_text(v, encoding="utf-8")
            pin_path = Path(td) / "codex-cli-binary-sha256.txt"
            pin_path.write_text(
                "# RETIRED tombstone (ADR-182) — no pin hex here\n",
                encoding="utf-8",
            )
            r = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--verdict-file", str(verdict_path),
                    "--codex-cli-binary-sha256-file", str(pin_path),
                    "--parent-sha", "a" * 40,
                    "--release-tag", "v1.99.0",
                ],
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
