"""Meta-tests for the hook stdout/exit-code contract oracle (PLAN-163 T2.1).

Red-first proofs that ``check-hook-stdout-schema.py`` has teeth:

- a synthetic wired hook that imports argparse FAILS the static check;
- a synthetic wired hook that exits nonzero on the infra path (via a
  NON-constant exit so the static pass stays green) FAILS the behavioral
  infra check;
- an argparse CLI from the allowlist (check_harness_config.py) WIRED as a
  hook is a violation;
- the versioned-snapshot slot rejects out-of-snapshot top-level keys;
- a REAL wired hook (check_bash_safety.py — the security-matcher
  precedent) passes paths (a) wired-set derivation, (b) infra fail-open,
  (c) input-parse fail-closed and (d) schema validation against the LIVE
  tree.

Staged with the PLAN-163 main-pack: the oracle it exercises ships in the
same pack, and the path resolution below works from BOTH the staged
layout (.claude/plans/PLAN-163/staged/main-pack/.claude/scripts/tests/)
and the post-ceremony canonical layout (.claude/scripts/tests/).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

_TESTS_DIR = Path(__file__).resolve().parent

# The oracle under test sits one directory up from this test file in BOTH
# layouts (staged pack and canonical scripts/).
_ORACLE = _TESTS_DIR.parent / "check-hook-stdout-schema.py"


def _find_repo_root(start: Path) -> Path:
    """Walk up to the real repo (marked by .git) — fingerprint-parity pattern."""
    for cand in [start, *start.parents]:
        if (cand / ".git").exists():
            return cand
    return start.parent.parent.parent  # pragma: no cover — legacy fallback


_REPO_ROOT = _find_repo_root(_TESTS_DIR)
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _run_oracle(
    args: List[str],
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> Tuple[int, str]:
    """Run the oracle with DETERMINISTIC dev-local snapshot semantics by
    default: ``CI`` / ``GITHUB_ACTIONS`` are stripped from the subprocess
    env so the require-snapshot CI auto-detection (M3/C7) does not depend on
    whether this suite itself runs under CI. Tests that exercise the
    fail-CLOSED path re-assert them explicitly via ``env``.
    """
    run_env = dict(os.environ)
    run_env.pop("CI", None)
    run_env.pop("GITHUB_ACTIONS", None)
    if env:
        run_env.update(env)
    proc = subprocess.run(
        [sys.executable, str(_ORACLE), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or _REPO_ROOT),
        env=run_env,
        timeout=180,
    )
    return proc.returncode, proc.stdout + proc.stderr


class HookStdoutSchemaOracleTest(TestEnvContext):
    """Synthetic-repo (red-first) + live-tree (green) meta-tests."""

    def _make_synthetic_repo(self, hook_name: str, hook_source: str) -> Path:
        """Build a minimal repo the oracle accepts: .git + settings.json +
        the wired hook. Lives inside the TestEnvContext temp tree."""
        repo = self.project_dir / "synthetic-repo"
        (repo / ".git").mkdir(parents=True)
        hooks = repo / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / hook_name).write_text(hook_source, encoding="utf-8")
        settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/'
                                    '_python-hook.sh" %s' % hook_name
                                ),
                                "timeout": 5,
                            }
                        ],
                    }
                ]
            }
        }
        (repo / ".claude" / "settings.json").write_text(
            json.dumps(settings), encoding="utf-8"
        )
        return repo

    # ------------------------------------------------------------------
    # RED-first: static check
    # ------------------------------------------------------------------

    def test_static_rejects_argparse_import_in_wired_hook(self) -> None:
        repo = self._make_synthetic_repo(
            "bad_argparse_hook.py",
            "import argparse\n"
            "import json, sys\n"
            "print(json.dumps({}))\n",
        )
        rc, out = _run_oracle(["--repo", str(repo), "--skip-behavioral"])
        self.assertEqual(rc, 1, "argparse-importing wired hook must RED the oracle:\n" + out)
        self.assertIn("argparse", out)
        self.assertIn("bad_argparse_hook.py", out)

    def test_static_rejects_constant_nonzero_exit(self) -> None:
        repo = self._make_synthetic_repo(
            "bad_exit_hook.py",
            "import sys\n"
            "print('{}')\n"
            "sys.exit(2)\n",
        )
        rc, out = _run_oracle(["--repo", str(repo), "--skip-behavioral"])
        self.assertEqual(rc, 1, "constant sys.exit(2) must RED the static check:\n" + out)
        self.assertIn("sys.exit(2)", out)

    def test_static_flags_wired_argparse_cli_from_allowlist(self) -> None:
        # check_harness_config.py keeps its exit!=0 argparse contract
        # (validate.yml harness-config gate) precisely BECAUSE it is not
        # wired; the oracle must scream if it ever appears wired.
        repo = self._make_synthetic_repo("check_harness_config.py", "print('{}')\n")
        rc, out = _run_oracle(["--repo", str(repo), "--skip-behavioral"])
        self.assertEqual(rc, 1, out)
        self.assertIn("WIRED as a hook", out)

    # ------------------------------------------------------------------
    # RED-first: behavioral infra path
    # ------------------------------------------------------------------

    def test_behavioral_catches_nonzero_exit_on_infra_path(self) -> None:
        # Non-constant exit status so the STATIC pass stays green and the
        # violation is attributable to the behavioral infra run alone.
        repo = self._make_synthetic_repo(
            "runtime_exit2_hook.py",
            "import sys\n"
            "sys.exit(int('2'))\n",
        )
        rc, out = _run_oracle(["--repo", str(repo)])
        self.assertEqual(rc, 1, "runtime exit 2 on the infra fixture must RED:\n" + out)
        self.assertIn("[infra]", out)
        self.assertIn("exit 2", out)

    def test_behavioral_catches_non_json_stdout(self) -> None:
        repo = self._make_synthetic_repo(
            "usage_text_hook.py",
            "print('usage: not-json [-h]')\n",
        )
        rc, out = _run_oracle(["--repo", str(repo)])
        self.assertEqual(rc, 1, out)
        self.assertIn("not JSON", out)

    def test_behavioral_green_on_wellformed_synthetic_hook(self) -> None:
        repo = self._make_synthetic_repo(
            "good_hook.py",
            "import json\n"
            "print(json.dumps({}))\n",
        )
        rc, out = _run_oracle(["--repo", str(repo)])
        self.assertEqual(rc, 0, "a {} + exit-0 hook must pass:\n" + out)

    # ------------------------------------------------------------------
    # Versioned schema snapshot slot (T2.2 / CF-5)
    # ------------------------------------------------------------------

    def test_snapshot_rejects_out_of_snapshot_keys(self) -> None:
        repo = self._make_synthetic_repo(
            "keyed_hook.py",
            "import json\n"
            "print(json.dumps({'decision': 'allow', 'systemMessage': 'x'}))\n",
        )
        snap = self.project_dir / "snap.json"
        snap.write_text(
            json.dumps({"allowed_top_level_keys": ["decision"]}), encoding="utf-8"
        )
        rc, out = _run_oracle(
            ["--repo", str(repo), "--schema-snapshot", str(snap)]
        )
        self.assertEqual(rc, 1, out)
        self.assertIn("systemMessage", out)

        snap.write_text(
            json.dumps({"allowed_top_level_keys": ["decision", "systemMessage"]}),
            encoding="utf-8",
        )
        rc, out = _run_oracle(
            ["--repo", str(repo), "--schema-snapshot", str(snap)]
        )
        self.assertEqual(rc, 0, out)

    def test_snapshot_absent_is_warning_not_violation(self) -> None:
        repo = self._make_synthetic_repo(
            "good_hook2.py",
            "print('{}')\n",
        )
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(self.project_dir / "does-not-exist.json"),
            ]
        )
        self.assertEqual(rc, 0, out)
        self.assertIn("SKIPPED", out)

    # ------------------------------------------------------------------
    # Fail-CLOSED in CI / --require-snapshot (M3/C7)
    # ------------------------------------------------------------------

    def _good_repo(self) -> Path:
        return self._make_synthetic_repo("good_ci_hook.py", "print('{}')\n")

    def test_require_snapshot_flag_fails_closed_on_absent(self) -> None:
        repo = self._good_repo()
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(self.project_dir / "nope.json"),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(rc, 1, "absent snapshot under --require-snapshot must RED:\n" + out)
        self.assertIn("FAIL-CLOSED", out)
        # The regeneration recipe must be actionable (cp + expected sha256).
        self.assertIn("cp ", out)
        self.assertIn(
            "acd9b05f8bf1d789c743f390a5218ababfe2c733ff13cdd49e78785c479abcee", out
        )

    def test_ci_env_fails_closed_on_absent(self) -> None:
        repo = self._good_repo()
        for var in ("CI", "GITHUB_ACTIONS"):
            rc, out = _run_oracle(
                [
                    "--repo",
                    str(repo),
                    "--schema-snapshot",
                    str(self.project_dir / "nope.json"),
                    "--skip-behavioral",
                ],
                env={var: "true"},
            )
            self.assertEqual(
                rc, 1, "%s=true must make absent snapshot fail-CLOSED:\n%s" % (var, out)
            )
            self.assertIn("FAIL-CLOSED", out)

    def test_ci_env_false_stays_warn(self) -> None:
        # A CI var explicitly turned off must NOT trip fail-closed.
        repo = self._good_repo()
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(self.project_dir / "nope.json"),
                "--skip-behavioral",
            ],
            env={"CI": "false", "GITHUB_ACTIONS": ""},
        )
        self.assertEqual(rc, 0, "CI=false must keep dev-local warn semantics:\n" + out)
        self.assertIn("SKIPPED", out)

    def test_require_snapshot_green_when_snapshot_present(self) -> None:
        repo = self._good_repo()
        snap = self.project_dir / "snap.json"
        snap.write_text(
            json.dumps({"allowed_top_level_keys": ["decision"]}), encoding="utf-8"
        )
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(snap),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(rc, 0, "present snapshot under --require-snapshot must pass:\n" + out)

    def test_require_snapshot_fails_closed_on_unreadable(self) -> None:
        repo = self._good_repo()
        snap = self.project_dir / "broken.json"
        snap.write_text("{ this is not json", encoding="utf-8")
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(snap),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(rc, 1, "unreadable snapshot under --require-snapshot must RED:\n" + out)
        self.assertIn("FAIL-CLOSED", out)

    def test_require_snapshot_fails_closed_on_unrecognized_shape(self) -> None:
        repo = self._good_repo()
        snap = self.project_dir / "empty-shape.json"
        # Valid JSON object, but no recognized key set → _load_snapshot None.
        snap.write_text(json.dumps({"unrelated": 1}), encoding="utf-8")
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(snap),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(
            rc, 1, "unrecognized-shape snapshot under --require-snapshot must RED:\n" + out
        )
        self.assertIn("FAIL-CLOSED", out)

    def test_require_snapshot_fails_closed_on_recognized_but_empty(self) -> None:
        # FXe (R2-M2): a snapshot of a RECOGNIZED shape whose allowed-key set
        # is EMPTY carries no versioned authority — the ``if allowed:`` guard
        # would skip every check (vacuous pass). Under --require-snapshot this
        # must fail CLOSED, exactly like an absent/unrecognized snapshot.
        repo = self._good_repo()
        for shape in (
            {"allowed_top_level_keys": []},
            {"properties": {}},
            {"common_output_schema": {}},
            {"events": {"PreToolUse": {"allowed_top_level_keys": []}}},
        ):
            snap = self.project_dir / "empty-keys.json"
            snap.write_text(json.dumps(shape), encoding="utf-8")
            rc, out = _run_oracle(
                [
                    "--repo",
                    str(repo),
                    "--schema-snapshot",
                    str(snap),
                    "--require-snapshot",
                    "--skip-behavioral",
                ]
            )
            self.assertEqual(
                rc,
                1,
                "recognized-but-empty snapshot %r under --require-snapshot must "
                "RED (no vacuous pass):\n%s" % (shape, out),
            )
            self.assertIn("FAIL-CLOSED", out)
            self.assertIn("NO validation keys", out)

    def test_empty_snapshot_dev_local_stays_warn(self) -> None:
        # Same recognized-but-empty snapshot in DEV-LOCAL (no --require-snapshot,
        # no CI env) keeps the warn-and-skip convenience: exit 0, SKIPPED noted.
        repo = self._good_repo()
        snap = self.project_dir / "empty-keys-dev.json"
        snap.write_text(json.dumps({"allowed_top_level_keys": []}), encoding="utf-8")
        rc, out = _run_oracle(
            ["--repo", str(repo), "--schema-snapshot", str(snap), "--skip-behavioral"]
        )
        self.assertEqual(rc, 0, "dev-local empty snapshot must warn+pass:\n" + out)
        self.assertIn("SKIPPED", out)

    def test_require_snapshot_fails_closed_on_mixed_empty_event(self) -> None:
        # FXζ (C7): a MIXED snapshot — one event with real keys, a SIBLING
        # event with an EMPTY allowed-key set — LOADS (the non-empty sibling
        # keeps it out of the wholly-empty FXe gate), yet the empty event's
        # versioned check is VACUOUS: ``allowed = events[ev] or global`` is
        # falsy/None, ``if allowed:`` skips it. Under --require-snapshot this
        # must fail CLOSED (a versioned gate that silently skips a declared
        # event has lost its authority) — additive to the wholly-empty case.
        repo = self._good_repo()
        snap = self.project_dir / "mixed-empty.json"
        snap.write_text(
            json.dumps(
                {
                    "events": {
                        "PreToolUse": {"allowed_top_level_keys": ["decision"]},
                        "Stop": {"allowed_top_level_keys": []},
                    }
                }
            ),
            encoding="utf-8",
        )
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(snap),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(
            rc,
            1,
            "mixed snapshot with an empty sibling event under "
            "--require-snapshot must RED (vacuous per-event validation):\n" + out,
        )
        self.assertIn("FAIL-CLOSED", out)
        # The offending event must be named, and the vacuous nature stated.
        self.assertIn("Stop", out)
        self.assertIn("EMPTY allowed-key set", out)

    def test_mixed_empty_event_dev_local_stays_warn(self) -> None:
        # Same mixed snapshot in DEV-LOCAL (no --require-snapshot, no CI env):
        # warn-and-validate. Exit 0; the empty-event warning is surfaced; the
        # snapshot stays active so the non-empty sibling still validates.
        repo = self._good_repo()
        snap = self.project_dir / "mixed-empty-dev.json"
        snap.write_text(
            json.dumps(
                {
                    "events": {
                        "PreToolUse": {"allowed_top_level_keys": ["decision"]},
                        "Stop": {"allowed_top_level_keys": []},
                    }
                }
            ),
            encoding="utf-8",
        )
        rc, out = _run_oracle(
            ["--repo", str(repo), "--schema-snapshot", str(snap), "--skip-behavioral"]
        )
        self.assertEqual(
            rc, 0, "dev-local mixed snapshot must warn+pass (not fail-closed):\n" + out
        )
        self.assertNotIn("FAIL-CLOSED", out)
        self.assertIn("EMPTY allowed-key set", out)
        self.assertIn("Stop", out)

    def test_require_snapshot_green_on_all_nonempty_per_event(self) -> None:
        # The FXζ gate must NOT false-positive: an events-shaped snapshot whose
        # per-event key sets are ALL non-empty carries full authority and
        # passes under --require-snapshot.
        repo = self._good_repo()
        snap = self.project_dir / "all-nonempty.json"
        snap.write_text(
            json.dumps(
                {
                    "events": {
                        "PreToolUse": {"allowed_top_level_keys": ["decision"]},
                        "Stop": {"allowed_top_level_keys": ["decision"]},
                    }
                }
            ),
            encoding="utf-8",
        )
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(snap),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(
            rc, 0, "all-non-empty per-event snapshot must pass --require-snapshot:\n" + out
        )
        self.assertNotIn("FAIL-CLOSED", out)

    def test_require_snapshot_is_additive_not_masking(self) -> None:
        # The snapshot fail-closed must NOT suppress or replace the other
        # oracle checks: an argparse-importing hook is still flagged, AND the
        # snapshot failure is reported — both in one run.
        repo = self._make_synthetic_repo(
            "argparse_and_missing_snap.py",
            "import argparse\nimport json\nprint(json.dumps({}))\n",
        )
        rc, out = _run_oracle(
            [
                "--repo",
                str(repo),
                "--schema-snapshot",
                str(self.project_dir / "nope.json"),
                "--require-snapshot",
                "--skip-behavioral",
            ]
        )
        self.assertEqual(rc, 1, out)
        self.assertIn("argparse", out)
        self.assertIn("FAIL-CLOSED", out)

    # ------------------------------------------------------------------
    # GREEN: a real wired hook against the LIVE tree
    # ------------------------------------------------------------------

    def test_real_wired_security_matcher_passes_all_paths(self) -> None:
        """check_bash_safety.py — the PLAN-152 C4 fail-closed precedent —
        must pass (a) derivation, (b) infra fail-open, (c) input-parse
        fail-closed and (d) schema validation against the live tree."""
        if not (_REPO_ROOT / ".claude" / "settings.json").is_file():
            self.skipTest("live settings.json not present (bare checkout)")
        rc, out = _run_oracle(["--only", "check_bash_safety.py", "--json"])
        self.assertEqual(rc, 0, "live check_bash_safety.py must pass the oracle:\n" + out)
        report = json.loads(out)
        entry = report["hooks"]["check_bash_safety.py"]
        self.assertEqual(entry["static"], [])
        self.assertEqual(entry["behavioral"], [])
        self.assertEqual(report["violations"], 0)

    def test_oracle_exits_2_on_unusable_repo(self) -> None:
        empty = self.project_dir / "empty"
        empty.mkdir()
        rc, out = _run_oracle(["--repo", str(empty)])
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    import unittest

    unittest.main()
