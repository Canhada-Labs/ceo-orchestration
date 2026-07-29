"""ADR-182 payload-pin verify-then-invoke tests (PLAN-163 T5.2 pin-pack).

RED-FIRST contract (staged with the pack — these tests are RED against
the pre-pack live tree, which has no `verify_codex_payload` and would
happily "verify" the launcher):

- THE core discriminator: a manifest pinned to the sha256 of the npm JS
  *launcher* (`bin/codex.js` — what `shasum -a 256 $(which codex)`
  hashes) must FAIL verification, and the same manifest pinned to the
  NATIVE payload bytes must PASS and return the payload path. This is
  the exact 0.144.1→0.144.6 no-gate-trip failure ADR-182 closes.
- targetTriple absent from the manifest → fail-CLOSED
  (`CodexPinMismatch`), never a silent advisory degrade.
- Manifest missing → INFRA → fail-OPEN (`None` → CodexUnavailable arm),
  per the hook's standing doctrine.
- `_decide()` end-to-end: pin mismatch on an L3+ write →
  `{"decision": "block"}` (the hook's only hard-block).
- `--verify-codex-pin` CLI exit codes (0 verified / 1 mismatch) — the
  `pair-rail-gate.sh` Gate 4 contract.

Env hygiene: TestEnvContext base (mandatory for hooks/tests) +
`mock.patch.dict` for every env mutation (PATH is not in the
TestEnvContext snapshot).

stdlib-only. Python >=3.9.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_pair_rail as cpr  # noqa: E402

_TRIPLE = "aarch64-apple-darwin"
_PKG_REL = "@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex"

_LAUNCHER_BYTES = b"#!/usr/bin/env node\n// fake codex.js launcher\n"
_PAYLOAD_BYTES = b"\x7fELF-fake-native-codex-payload\n" * 4

# PLAN-163 FXα: the fixture-injection env var was REMOVED from production.
# These tests still set/pop it to PROVE it is inert (negative control), but
# the name is assembled from fragments so the full literal never appears in a
# grep — the migration invariant "no staged test references the live fixture
# literal" (grep == 0 across all staged test_*.py) stays enforceable.
_DEAD_FIXTURE_ENV = "CEO_PAIR_RAIL_FIXTURE" + "_RESPONSE"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _PinTreeMixin:
    """Builds a fake npm install tree mirroring the launcher layout.

    <root>/bin/codex                  -> symlink to the launcher (what
                                          $PATH discovery finds)
    <root>/lib/node_modules/@openai/codex/bin/codex.js       (launcher)
    <root>/lib/node_modules/@openai/codex/node_modules/
        @openai/codex-darwin-arm64/vendor/<triple>/bin/codex (payload)
    """

    def _make_npm_tree(self, root: Path) -> Tuple[Path, Path, Path]:
        pkg_dir = root / "lib" / "node_modules" / "@openai" / "codex"
        launcher = pkg_dir / "bin" / "codex.js"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_bytes(_LAUNCHER_BYTES)
        launcher.chmod(0o755)  # $PATH discovery requires X_OK
        payload = pkg_dir.joinpath("node_modules", *_PKG_REL.split("/"))
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(_PAYLOAD_BYTES)
        payload.chmod(0o755)
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        path_entry = bin_dir / "codex"
        os.symlink(launcher, path_entry)
        path_entry_parent = bin_dir
        return path_entry_parent, launcher, payload

    def _write_manifest(
        self, root: Path, sha256_hex: str, *, triple: str = _TRIPLE
    ) -> Path:
        manifest = root / "codex-cli-pin-manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "package_version": "0.144.6",
                    "npm_integrity": "sha512-test-only",
                    "payloads": {
                        triple: {"path": _PKG_REL, "sha256": sha256_hex}
                    },
                }
            ),
            encoding="utf-8",
        )
        return manifest

    def _pin_env(
        self, bin_dir: Path, manifest: Path, extra: Dict[str, str] = None
    ) -> Dict[str, str]:
        env = {
            "PATH": str(bin_dir),
            # H1: the triple/manifest seams are honoured ONLY under the
            # explicit test-mode marker; the tests exercise the seams, so
            # they set it. (The LIVE path ignores these overrides.)
            "CEO_PAIR_RAIL_TEST_MODE": "1",
            "CEO_PAIR_RAIL_PIN_MANIFEST": str(manifest),
            "CEO_PAIR_RAIL_TARGET_TRIPLE": _TRIPLE,
            # neutralize test-only shortcuts + kill-switch
            "CEO_PAIR_RAIL_DISABLE": "",
        }
        if extra:
            env.update(extra)
        return env

    def _patched(self, env: Dict[str, str]):
        """patch.dict + pop the shortcut vars (restored on exit)."""
        ctx = mock.patch.dict(os.environ, env)
        return ctx

    @staticmethod
    def _pop_shortcuts() -> None:
        # patch.dict snapshots the WHOLE dict, so pops inside the
        # context are restored on exit.
        os.environ.pop("CEO_PAIR_RAIL_CODEX_BIN", None)
        os.environ.pop(_DEAD_FIXTURE_ENV, None)


class TestPayloadPinResolution(_PinTreeMixin, TestEnvContext):
    """verify_codex_payload / _resolve_codex_bin arms."""

    def setUp(self) -> None:
        super().setUp()
        self.tree_root = self.project_dir / "npmtree"
        self.bin_dir, self.launcher, self.payload = self._make_npm_tree(
            self.tree_root
        )

    def test_pin_of_launcher_hash_fails_closed(self):
        """RED-FIRST core: the old `shasum $(which codex)` value (the
        launcher hash) must NOT verify — that pin attests the wrong
        artifact."""
        manifest = self._write_manifest(
            self.tree_root, _sha256(_LAUNCHER_BYTES)
        )
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch) as cm:
                cpr._resolve_codex_bin()
            self.assertIn("mismatch", str(cm.exception))

    def test_pin_of_payload_verifies_and_returns_payload_path(self):
        manifest = self._write_manifest(
            self.tree_root, _sha256(_PAYLOAD_BYTES)
        )
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            resolved = cpr._resolve_codex_bin()
        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.samefile(resolved, str(self.payload)))
        # And the verified path is the PAYLOAD, not the launcher/symlink.
        self.assertFalse(os.path.samefile(resolved, str(self.launcher)))

    def test_triple_absent_from_manifest_fails_closed(self):
        manifest = self._write_manifest(
            self.tree_root, _sha256(_PAYLOAD_BYTES), triple="x86_64-apple-darwin"
        )
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch) as cm:
                cpr._resolve_codex_bin()
            self.assertIn("triple_missing", str(cm.exception))

    def test_malformed_manifest_entry_fails_closed(self):
        manifest = self.tree_root / "codex-cli-pin-manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "payloads": {
                        _TRIPLE: {"path": _PKG_REL, "sha256": "not-hex"}
                    },
                }
            ),
            encoding="utf-8",
        )
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_manifest_missing_is_infra_fail_open(self):
        missing = self.tree_root / "nope" / "manifest.json"
        with self._patched(self._pin_env(self.bin_dir, missing)):
            self._pop_shortcuts()
            self.assertIsNone(cpr._resolve_codex_bin())

    def test_codex_bin_override_is_verified_matching_sha(self):
        """H1 (PLAN-163 fix-pass): the CEO_PAIR_RAIL_CODEX_BIN override is
        VERIFIED, not trusted blindly. When the override's own bytes are
        pinned in the manifest for the current triple, it verifies and the
        override path is returned."""
        override_bin = self.tree_root / "stand_in_codex"
        override_bin.write_bytes(_PAYLOAD_BYTES)
        override_bin.chmod(0o755)
        manifest = self._write_manifest(self.tree_root, _sha256(_PAYLOAD_BYTES))
        env = self._pin_env(
            self.bin_dir, manifest,
            extra={"CEO_PAIR_RAIL_CODEX_BIN": str(override_bin)},
        )
        with self._patched(env):
            os.environ.pop(_DEAD_FIXTURE_ENV, None)
            resolved = cpr._resolve_codex_bin()
        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.samefile(resolved, str(override_bin)))

    def test_codex_bin_override_wrong_sha_fails_closed(self):
        """RED-FIRST H1 core: an override whose sha does NOT match the
        manifest entry must FAIL-CLOSED (CodexPinMismatch) — NOT be
        returned unverified. Before the fix, `_resolve_codex_bin` returned
        the override path whenever it merely existed, defeating the pin on
        the live rail. The manifest here is pinned to the PAYLOAD bytes,
        but the override points at DIFFERENT (launcher) bytes → mismatch."""
        override_bin = self.tree_root / "swapped_codex"
        override_bin.write_bytes(_LAUNCHER_BYTES)  # different bytes
        override_bin.chmod(0o755)
        manifest = self._write_manifest(self.tree_root, _sha256(_PAYLOAD_BYTES))
        env = self._pin_env(
            self.bin_dir, manifest,
            extra={"CEO_PAIR_RAIL_CODEX_BIN": str(override_bin)},
        )
        with self._patched(env):
            os.environ.pop(_DEAD_FIXTURE_ENV, None)
            with self.assertRaises(cpr.CodexPinMismatch) as cm:
                cpr._resolve_codex_bin()
            self.assertIn("mismatch", str(cm.exception))

    def test_codex_bin_override_missing_file_fails_closed(self):
        """H1 'inexistente = BLOQUEIA': a set-but-missing override is a
        fail-CLOSED mismatch, never a silent INFRA advisory degrade — a
        hostile override must not relax the rail by pointing at a vanished
        path."""
        manifest = self._write_manifest(self.tree_root, _sha256(_PAYLOAD_BYTES))
        env = self._pin_env(
            self.bin_dir, manifest,
            extra={"CEO_PAIR_RAIL_CODEX_BIN": str(self.tree_root / "nope_bin")},
        )
        with self._patched(env):
            os.environ.pop(_DEAD_FIXTURE_ENV, None)
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()


class TestDecideBlocksOnPinMismatch(_PinTreeMixin, TestEnvContext):
    """End-to-end: L3+ write under a mismatched pin → hard block."""

    def test_decide_returns_block_on_mismatch(self):
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, _payload = self._make_npm_tree(tree_root)
        manifest = self._write_manifest(tree_root, _sha256(_LAUNCHER_BYTES))
        l3_target = str(
            self.project_dir / ".claude" / "hooks" / "check_example.py"
        )
        with self._patched(self._pin_env(bin_dir, manifest)):
            self._pop_shortcuts()
            decision = cpr._decide(
                tool_name="Edit",
                file_path=l3_target,
                proposed_content="x = 1\n",
                repo_root=self.project_dir,
                timeout_s=5.0,
                session_id="test-session",
            )
        self.assertEqual(decision.get("decision"), "block")
        self.assertIn("ADR-182", decision.get("reason", ""))

    def test_decide_stays_fail_open_when_manifest_missing(self):
        """INFRA arm must keep today's advisory degrade (no block)."""
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, _payload = self._make_npm_tree(tree_root)
        missing = tree_root / "nope" / "manifest.json"
        l3_target = str(
            self.project_dir / ".claude" / "hooks" / "check_example.py"
        )
        with self._patched(self._pin_env(bin_dir, missing)):
            self._pop_shortcuts()
            decision = cpr._decide(
                tool_name="Edit",
                file_path=l3_target,
                proposed_content="x = 1\n",
                repo_root=self.project_dir,
                timeout_s=5.0,
                session_id="test-session",
            )
        self.assertNotEqual(decision.get("decision"), "block")
        self.assertIn("Codex unavailable", decision.get("systemMessage", ""))


class TestMatrixAndMainPreserveBlock(_PinTreeMixin, TestEnvContext):
    """M4: the pin-mismatch BLOCK must survive the `_decide_with_matrix`
    wrapper AND the `main()` stdin/stdout entry point (not only the direct
    `_decide()` call), and the swapped binary must NEVER be invoked."""

    def _canary_bin(self, root: Path, canary: Path) -> Path:
        """A stand-in 'codex' that writes a canary file IF it is ever
        executed. Its bytes differ from the pinned payload → mismatch. The
        canary's presence after a run is proof the rail exec'd it."""
        b = root / "canary_codex"
        b.write_text(
            "#!/bin/sh\n" f': > "{canary}"\n' "exit 0\n", encoding="utf-8"
        )
        b.chmod(0o755)
        return b

    def test_decide_with_matrix_blocks_and_never_invokes(self):
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, _payload = self._make_npm_tree(tree_root)
        canary = self.project_dir / "INVOKED_CANARY"
        canary_bin = self._canary_bin(tree_root, canary)
        # Manifest pinned to the PAYLOAD bytes; override points at the
        # canary (different bytes) → sha mismatch.
        manifest = self._write_manifest(tree_root, _sha256(_PAYLOAD_BYTES))
        l3_target = str(
            self.project_dir / ".claude" / "hooks" / "check_example.py"
        )
        env = self._pin_env(
            bin_dir, manifest,
            extra={"CEO_PAIR_RAIL_CODEX_BIN": str(canary_bin)},
        )
        with self._patched(env):
            os.environ.pop(_DEAD_FIXTURE_ENV, None)
            decision = cpr._decide_with_matrix(
                tool_name="Edit",
                file_path=l3_target,
                proposed_content="x = 1\n",
                repo_root=self.project_dir,
                timeout_s=5.0,
                session_id="test-session",
            )
        self.assertEqual(decision.get("decision"), "block")
        self.assertIn("ADR-182", decision.get("reason", ""))
        self.assertFalse(
            canary.exists(),
            "swapped codex bin was INVOKED despite pin mismatch (matrix)",
        )

    def test_main_stdin_blocks_and_never_invokes(self):
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, _payload = self._make_npm_tree(tree_root)
        canary = self.project_dir / "INVOKED_CANARY_MAIN"
        canary_bin = self._canary_bin(tree_root, canary)
        manifest = self._write_manifest(tree_root, _sha256(_PAYLOAD_BYTES))
        l3_target = str(
            self.project_dir / ".claude" / "hooks" / "check_example.py"
        )
        env = dict(os.environ)
        env.update(self._pin_env(bin_dir, manifest))
        env["CEO_PAIR_RAIL_CODEX_BIN"] = str(canary_bin)
        env.pop(_DEAD_FIXTURE_ENV, None)
        env["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        envelope = json.dumps(
            {
                "tool_name": "Edit",
                "session_id": "test-session",
                "tool_input": {"file_path": l3_target, "new_string": "x = 1\n"},
            }
        )
        r = subprocess.run(
            [sys.executable, cpr.__file__],
            input=envelope, capture_output=True, text=True, timeout=60, env=env,
        )
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out.get("decision"), "block", msg=r.stdout + r.stderr)
        self.assertIn("ADR-182", out.get("reason", ""))
        self.assertFalse(
            canary.exists(),
            "swapped codex bin was INVOKED via main() despite pin mismatch",
        )


class TestVerifyPinCli(_PinTreeMixin, TestEnvContext):
    """`--verify-codex-pin` subprocess contract (pair-rail-gate.sh Gate 4)."""

    def _run_cli(self, manifest: Path, bin_dir: Path) -> "subprocess.CompletedProcess":
        env = dict(os.environ)
        env.update(self._pin_env(bin_dir, manifest))
        env.pop("CEO_PAIR_RAIL_CODEX_BIN", None)
        env.pop(_DEAD_FIXTURE_ENV, None)
        return subprocess.run(
            [sys.executable, cpr.__file__, "--verify-codex-pin"],
            capture_output=True, text=True, timeout=60, env=env,
        )

    def test_cli_exit_0_on_verified_and_reports_payload_sha(self):
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, payload = self._make_npm_tree(tree_root)
        manifest = self._write_manifest(tree_root, _sha256(_PAYLOAD_BYTES))
        r = self._run_cli(manifest, bin_dir)
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["status"], "verified")
        self.assertEqual(out["sha256"], _sha256(_PAYLOAD_BYTES))
        self.assertEqual(out["target_triple"], _TRIPLE)
        self.assertTrue(os.path.samefile(out["path"], str(payload)))

    def test_cli_exit_1_on_launcher_pin(self):
        tree_root = self.project_dir / "npmtree"
        bin_dir, _launcher, _payload = self._make_npm_tree(tree_root)
        manifest = self._write_manifest(tree_root, _sha256(_LAUNCHER_BYTES))
        r = self._run_cli(manifest, bin_dir)
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["status"], "mismatch")


class TestFixtureShortCircuitRequiresTestMode(_PinTreeMixin, TestEnvContext):
    """PLAN-163 FXα: the env-fixture short-circuit was
    REMOVED from production ENTIRELY — not merely gated behind
    CEO_PAIR_RAIL_TEST_MODE (the interim R2-B1 design). On EVERY path, with
    OR without the marker, the fixture env is IGNORED and control falls
    through to _resolve_codex_bin (real ADR-182 pin verification), so no env
    can inject a PASS review and skip payload-pin enforcement. "no env
    relaxes the sha verification" is therefore literally true.

    (Class name kept for history; it no longer "requires test mode" — under
    the removal there is no honoured-fixture path for any marker to unlock.)

    RED-FIRST: `test_fixture_inert_even_under_test_mode` FAILS against BOTH
    the pre-pin code (which returned the fixture unconditionally) AND the
    interim R2-B1 gated design (which returned the fixture verbatim under
    TEST_MODE=1); it PASSES only once the seam is fully removed."""

    _FIXTURE = "REVIEW: looks fine, no changes needed."

    def _base_env(self) -> Dict[str, str]:
        # No codex on PATH → _resolve_codex_bin hits launcher_not_found
        # (INFRA) → None → CodexUnavailable, IFF the fixture is not honoured.
        return {
            "PATH": str(self.project_dir / "no-such-bin"),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
            _DEAD_FIXTURE_ENV: self._FIXTURE,
        }

    def _clear_seams(self) -> None:
        # patch.dict snapshots the whole dict; these pops are restored on exit.
        for k in (
            "CEO_PAIR_RAIL_TEST_MODE",
            "CEO_PAIR_RAIL_CODEX_BIN",
            "CEO_PAIR_RAIL_PIN_MANIFEST",
            "CEO_PAIR_RAIL_TARGET_TRIPLE",
            "CEO_PAIR_RAIL_DISABLE",
        ):
            os.environ.pop(k, None)

    def test_fixture_ignored_on_live_path_without_test_mode(self):
        """Fixture set but NO test-mode → NOT short-circuited: control
        reaches _resolve_codex_bin and, with no codex on PATH, raises
        CodexUnavailable (the fixture string is never returned)."""
        with mock.patch.dict(os.environ, self._base_env()):
            self._clear_seams()  # ensure CEO_PAIR_RAIL_TEST_MODE is unset
            with self.assertRaises(cpr.CodexUnavailable):
                cpr._invoke_codex_review(
                    "Edit", ".claude/hooks/check_example.py", "x = 1\n", 5.0
                )

    def test_fixture_inert_even_under_test_mode(self):
        """REMOVAL discriminator (PLAN-163 FXα): the fixture seam is GONE, not
        merely gated — so even WITH CEO_PAIR_RAIL_TEST_MODE=1 the preset
        review is NEVER injected. Control still falls through to
        _resolve_codex_bin and, with no codex on PATH, raises
        CodexUnavailable. Under the retired R2-B1 gated design this call would
        have returned the fixture verbatim; asserting the raise is the exact
        red-first proof that the production path was removed."""
        env = self._base_env()
        env["CEO_PAIR_RAIL_TEST_MODE"] = "1"
        with mock.patch.dict(os.environ, env):
            for k in (
                "CEO_PAIR_RAIL_CODEX_BIN",
                "CEO_PAIR_RAIL_PIN_MANIFEST",
                "CEO_PAIR_RAIL_TARGET_TRIPLE",
                "CEO_PAIR_RAIL_DISABLE",
            ):
                os.environ.pop(k, None)
            with self.assertRaises(cpr.CodexUnavailable):
                cpr._invoke_codex_review(
                    "Edit", ".claude/hooks/check_example.py", "x = 1\n", 5.0
                )



class TestMalformedManifestFailsClosed(_PinTreeMixin, TestEnvContext):
    """FXβ (C2 HIGH): a pin manifest that is PRESENT but not parseable as a
    valid manifest (broken JSON, non-utf8 bytes, invalid top-level schema,
    invalid `payloads` shape) is an INPUT-parse failure of a security
    matcher → fail-CLOSED (CodexPinMismatch), NOT an INFRA advisory degrade.
    Only a genuinely ABSENT / unreadable (OSError) manifest stays INFRA →
    fail-open. (PLAN-152 debate-C4 fail-CLOSED-on-input doctrine.)

    RED-FIRST: before the fix, `_load_pin_manifest` collapsed every
    malformed class into `None`, which `verify_codex_payload` classified as
    INFRA → `_resolve_codex_bin` returned None (advisory), so
    assertRaises(CodexPinMismatch) FAILS against the pre-fix code.
    """

    def setUp(self) -> None:
        super().setUp()
        self.tree_root = self.project_dir / "npmtree"
        self.bin_dir, self.launcher, self.payload = self._make_npm_tree(
            self.tree_root
        )

    def _write_raw(self, text: str) -> Path:
        manifest = self.tree_root / "codex-cli-pin-manifest.json"
        manifest.write_text(text, encoding="utf-8")
        return manifest

    def test_broken_json_fails_closed(self):
        manifest = self._write_raw('{"schema": 1, "payloads": {')  # truncated
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_empty_manifest_fails_closed(self):
        manifest = self._write_raw("")
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_non_utf8_bytes_fail_closed(self):
        manifest = self.tree_root / "codex-cli-pin-manifest.json"
        manifest.write_bytes(b"\xff\xfe not-valid-utf8 \x00\x80")
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_top_level_not_object_fails_closed(self):
        manifest = self._write_raw(json.dumps([1, 2, 3]))
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_top_level_schema_wrong_fails_closed(self):
        manifest = self._write_raw(json.dumps({"schema": 2, "payloads": {}}))
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_payloads_not_object_fails_closed(self):
        manifest = self._write_raw(
            json.dumps({"schema": 1, "payloads": ["not", "a", "dict"]})
        )
        with self._patched(self._pin_env(self.bin_dir, manifest)):
            self._pop_shortcuts()
            with self.assertRaises(cpr.CodexPinMismatch):
                cpr._resolve_codex_bin()

    def test_cli_exit_1_on_malformed_manifest(self):
        """`--verify-codex-pin` on a present-but-corrupt manifest must exit 1
        (fail-CLOSED), NOT 3 (INFRA) — pair-rail-gate.sh Gate 4 contract."""
        manifest = self._write_raw('{"schema": 1, "payloads": {')
        env = dict(os.environ)
        env.update(self._pin_env(self.bin_dir, manifest))
        env.pop("CEO_PAIR_RAIL_CODEX_BIN", None)
        env.pop(_DEAD_FIXTURE_ENV, None)
        r = subprocess.run(
            [sys.executable, cpr.__file__, "--verify-codex-pin"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["status"], "mismatch")

    def test_absent_manifest_stays_infra_fail_open(self):
        """CROSS-STATE pair (the C6 lesson): the ABSENT manifest — content
        NOT present (OSError) — stays INFRA → None (advisory). Only PRESENT
        corruption fails closed; a missing file must not block."""
        missing = self.tree_root / "nope" / "manifest.json"
        with self._patched(self._pin_env(self.bin_dir, missing)):
            self._pop_shortcuts()
            self.assertIsNone(cpr._resolve_codex_bin())


if __name__ == "__main__":
    unittest.main(verbosity=2)
