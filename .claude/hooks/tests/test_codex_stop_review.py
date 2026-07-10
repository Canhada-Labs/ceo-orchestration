#!/usr/bin/env python3
"""PLAN-155 Wave 6 — inverted pair-rail Stop-review gate tests.

Two layers:

- **In-process unit tests** over the pure surfaces (``parse_verdict``,
  ``fingerprint``, ``l3_paths``, the review-log round-trip, ``decide``'s
  branch table, ``build_review_instruction`` content).
- **Subprocess behavioral controls** (the S254 anti-dead-gate doctrine):
  the landed hook is executed as a SUBPROCESS under ``CEO_HOOK_ADAPTER=codex``
  on a tmpdir copy of the live hooks tree (which post-landing already
  contains the wave-1 host adapter/seam and this wave's hook), fed a
  recorded-shape codex Stop envelope on stdin. A canonical edit with NO
  review record MUST come back ``{"decision":"block", ...}`` on the codex
  wire; adding an APPROVE record flips it to ``{}`` allow. A mutation
  control (blind the record match) proves the block assertion has teeth.

The tmpdir copy preserves the no-repo-tree-writes isolation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

_THIS = Path(__file__).resolve()
# Landed location: .claude/hooks/tests/test_...py -> repo root is 3 parents up.
# Resolve the repo root by walking up to the dir containing ".git".
def _repo_root() -> Path:
    p = _THIS
    for _ in range(12):
        if (p / ".git").exists():
            return p
        p = p.parent
    # Fallback: assume the landed depth.
    return _THIS.parents[3]


REPO = _repo_root()
# Post-landing (SENT-CX-D): the hook lives in the real hooks tree — the
# staged overlay copy is gitignored and absent in CI checkouts.
HOOKS_LIVE = REPO / ".claude" / "hooks"
HOOK_SRC = HOOKS_LIVE / "check_codex_stop_review.py"

# Make the landed hook importable in-process for the unit tests.
sys.path.insert(0, str(HOOKS_LIVE))
import importlib.util as _ilu  # noqa: E402


def _load_hook_module():
    spec = _ilu.spec_from_file_location("check_codex_stop_review_w6", str(HOOK_SRC))
    assert spec and spec.loader
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


MOD = _load_hook_module()


# ---------------------------------------------------------------------------
# In-process unit tests
# ---------------------------------------------------------------------------

class ParseVerdictTests(unittest.TestCase):
    def test_explicit_approve(self):
        v, f = MOD.parse_verdict("some prose\nVERDICT: APPROVE\n")
        self.assertEqual(v, "APPROVE")

    def test_explicit_reject_with_findings(self):
        v, f = MOD.parse_verdict(
            "issues:\n.claude/hooks/x.py:42 bad thing\nVERDICT: REJECT\n"
        )
        self.assertEqual(v, "REJECT")
        self.assertIn(".claude/hooks/x.py:42", f)

    def test_empty_is_unavailable_not_approve(self):
        # RED-on-absence: a silent reviewer is NEVER a fabricated APPROVE.
        self.assertEqual(MOD.parse_verdict("")[0], "UNAVAILABLE")
        self.assertEqual(MOD.parse_verdict("   \n  ")[0], "UNAVAILABLE")

    def test_no_verdict_token_is_unavailable(self):
        self.assertEqual(MOD.parse_verdict("looks fine to me")[0], "UNAVAILABLE")

    def test_reject_wins_over_approve(self):
        # Both bare tokens present, no VERDICT: line -> stricter reading.
        v, _ = MOD.parse_verdict("APPROVE parts but also REJECT parts")
        self.assertEqual(v, "REJECT")


class FingerprintTests(unittest.TestCase):
    def test_order_independent(self):
        a = MOD.fingerprint(["b", "a", "c"])
        b = MOD.fingerprint(["c", "b", "a", "a"])
        self.assertEqual(a, b)

    def test_matches_bash_joining(self):
        # Python: sha256("\n".join(sorted(set(paths)))). Pin one value so the
        # bash pre-push gate can be cross-checked against the same recipe.
        import hashlib
        paths = [".claude/hooks/z.py", ".github/workflows/validate.yml"]
        expected = hashlib.sha256(
            "\n".join(sorted(set(paths))).encode("utf-8")
        ).hexdigest()
        self.assertEqual(MOD.fingerprint(paths), expected)


class ReviewLogRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(
            __import__("tempfile").mkdtemp(prefix="w6-reviewlog-")
        )
        self._prev = os.environ.get("CEO_CODEX_REVIEW_STATE_DIR")
        os.environ["CEO_CODEX_REVIEW_STATE_DIR"] = str(self._tmp)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("CEO_CODEX_REVIEW_STATE_DIR", None)
        else:
            os.environ["CEO_CODEX_REVIEW_STATE_DIR"] = self._prev
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_append_and_match_by_fingerprint(self):
        fp = MOD.fingerprint([".claude/hooks/a.py"])
        MOD._append_review_record(
            {
                "session_id": "sess-1",
                "verdict": "APPROVE",
                "reviewer_model": "claude-opus-4-8",
                "fingerprint": fp,
                "findings": [],
                "ts": "2026-07-10T00:00:00Z",
            }
        )
        rec = MOD.latest_review_record("sess-1", fp)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["verdict"], "APPROVE")

    def test_nonmatching_fingerprint_not_returned(self):
        MOD._append_review_record(
            {
                "session_id": "sess-1",
                "verdict": "APPROVE",
                "fingerprint": "deadbeef",
                "ts": "x",
            }
        )
        self.assertIsNone(MOD.latest_review_record("sess-1", "otherfp"))

    def test_latest_wins(self):
        fp = "fp"
        MOD._append_review_record(
            {"session_id": "s", "verdict": "REJECT", "fingerprint": fp, "ts": "1"}
        )
        MOD._append_review_record(
            {"session_id": "s", "verdict": "APPROVE", "fingerprint": fp, "ts": "2"}
        )
        self.assertEqual(MOD.latest_review_record("s", fp)["verdict"], "APPROVE")


class _GitRepoMixin:
    """Build a throwaway git repo with staged canonical + non-canonical edits."""

    def _make_repo(self, canonical: bool):
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="w6-git-"))
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "t@t"], check=True
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", "t"], check=True
        )
        # Seed a commit so HEAD exists.
        (root / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True
        )
        if canonical:
            target = root / ".claude" / "hooks" / "edited.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# canonical edit\n", encoding="utf-8")
        else:
            (root / "notes.txt").write_text("plain edit\n", encoding="utf-8")
        return root


class L3PathsTests(unittest.TestCase, _GitRepoMixin):
    def test_detects_canonical_untracked(self):
        root = self._make_repo(canonical=True)
        try:
            paths = MOD.l3_paths(root)
            self.assertTrue(
                any(p.startswith(".claude/") for p in paths),
                "expected a .claude/ path in %r" % paths,
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ignores_noncanonical(self):
        root = self._make_repo(canonical=False)
        try:
            self.assertEqual(MOD.l3_paths(root), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class DecideBranchTests(unittest.TestCase, _GitRepoMixin):
    def setUp(self):
        self._tmp = Path(__import__("tempfile").mkdtemp(prefix="w6-decide-"))
        self._prev = os.environ.get("CEO_CODEX_REVIEW_STATE_DIR")
        os.environ["CEO_CODEX_REVIEW_STATE_DIR"] = str(self._tmp)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("CEO_CODEX_REVIEW_STATE_DIR", None)
        else:
            os.environ["CEO_CODEX_REVIEW_STATE_DIR"] = self._prev
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_l3_paths_allows(self):
        root = self._make_repo(canonical=False)
        try:
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=False
            )
            self.assertTrue(allow)
            self.assertFalse(red)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_canonical_no_record_blocks(self):
        root = self._make_repo(canonical=True)
        try:
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=False
            )
            self.assertFalse(allow)
            self.assertIn("STOP GATE", reason)
            self.assertIn("Claude reviews", reason)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_canonical_approve_record_allows(self):
        root = self._make_repo(canonical=True)
        try:
            fp = MOD.fingerprint(MOD.l3_paths(root))
            MOD._append_review_record(
                {
                    "session_id": "s",
                    "verdict": "APPROVE",
                    "reviewer_model": "claude-opus-4-8",
                    "fingerprint": fp,
                    "findings": [],
                    "ts": "x",
                }
            )
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=False
            )
            self.assertTrue(allow)
            self.assertIn("APPROVE", sysmsg)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_canonical_reject_record_blocks(self):
        root = self._make_repo(canonical=True)
        try:
            fp = MOD.fingerprint(MOD.l3_paths(root))
            MOD._append_review_record(
                {
                    "session_id": "s",
                    "verdict": "REJECT",
                    "fingerprint": fp,
                    "findings": [".claude/hooks/edited.py:1"],
                    "ts": "x",
                }
            )
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=False
            )
            self.assertFalse(allow)
            self.assertIn("REJECT", reason)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_loop_guard_no_record_allows_with_red(self):
        # stop_hook_active + no record => abandoned; allow-with-loud + RED.
        root = self._make_repo(canonical=True)
        try:
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=True
            )
            self.assertTrue(allow)
            self.assertTrue(red)
            self.assertIn("ABANDONED", sysmsg)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_unavailable_record_allows_with_red(self):
        root = self._make_repo(canonical=True)
        try:
            fp = MOD.fingerprint(MOD.l3_paths(root))
            MOD._append_review_record(
                {"session_id": "s", "verdict": "UNAVAILABLE", "fingerprint": fp, "ts": "x"}
            )
            allow, reason, sysmsg, red = MOD.decide(
                repo_root=root, session_id="s", stop_hook_active=False
            )
            self.assertTrue(allow)
            self.assertTrue(red)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class InstructionTests(unittest.TestCase):
    def test_instruction_carries_pin_and_neutral_caveat(self):
        txt = MOD.build_review_instruction(
            session_id="sess", paths=[".claude/hooks/x.py"], repo_root=Path("/repo")
        )
        self.assertIn("claude-opus-4-8", txt)
        self.assertIn("CEO_PAIR_RAIL_REVIEWER_MODEL", txt)
        self.assertIn("OpenAI Codex", txt)
        self.assertIn("Anthropic Claude", txt)
        self.assertIn("--record", txt)

    def test_reviewer_model_override(self):
        prev = os.environ.get("CEO_PAIR_RAIL_REVIEWER_MODEL")
        os.environ["CEO_PAIR_RAIL_REVIEWER_MODEL"] = "claude-test-tier"
        try:
            self.assertEqual(MOD.reviewer_model(), "claude-test-tier")
        finally:
            if prev is None:
                os.environ.pop("CEO_PAIR_RAIL_REVIEWER_MODEL", None)
            else:
                os.environ["CEO_PAIR_RAIL_REVIEWER_MODEL"] = prev


# ---------------------------------------------------------------------------
# Subprocess behavioral controls (S254 anti-dead-gate; codex-wire emit)
# ---------------------------------------------------------------------------

def _build_overlay() -> Path:
    """Copy the landed hooks tree into an isolated tmpdir.

    Post-landing the live tree already contains the wave-1 seam/adapter
    and this wave's hook — no staged overlay composition is needed; the
    tmpdir copy only preserves the no-repo-tree-writes isolation.
    """
    import tempfile
    dst = Path(tempfile.mkdtemp(prefix="w6-overlay-")) / "hooks"
    shutil.copytree(HOOKS_LIVE, dst)
    return dst


def _stop_envelope(session_id: str, cwd: str, stop_hook_active: bool) -> str:
    return json.dumps(
        {
            "session_id": session_id,
            "transcript_path": "/tmp/codex-lab/t.jsonl",
            "cwd": cwd,
            "hook_event_name": "Stop",
            "model": "gpt-5.5",
            "permission_mode": "bypassPermissions",
            "stop_hook_active": stop_hook_active,
            "last_assistant_message": "done",
        }
    )


class SubprocessStopWireTests(unittest.TestCase, _GitRepoMixin):
    @classmethod
    def setUpClass(cls):
        cls.overlay = _build_overlay()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.overlay.parent, ignore_errors=True)

    def _run(self, repo_root: Path, envelope: str, state_dir: Path):
        env = dict(os.environ)
        env["CEO_HOOK_ADAPTER"] = "codex"
        env["CLAUDE_PROJECT_DIR"] = str(repo_root)
        env["CEO_CODEX_REVIEW_STATE_DIR"] = str(state_dir)
        env["CEO_AUDIT_LOG_DIR"] = str(state_dir)
        env["CEO_AUDIT_LOG_ERR"] = str(state_dir / "audit-log.errors")
        proc = subprocess.run(
            [sys.executable, str(self.overlay / "check_codex_stop_review.py")],
            input=envelope.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=30,
        )
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        try:
            return json.loads(out), proc
        except Exception:
            self.fail("hook stdout not JSON: %r (stderr=%r)" % (out, proc.stderr[:400]))

    def test_canonical_no_record_denies_on_codex_wire(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-sp-state-"))
        root = self._make_repo(canonical=True)
        try:
            obj, _ = self._run(root, _stop_envelope("sp-1", str(root), False), state)
            # Codex Stop-block wire (verified 0.139): {"decision":"block","reason":...}
            self.assertEqual(obj.get("decision"), "block")
            self.assertIn("STOP GATE", obj.get("reason", ""))
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_approve_record_allows_on_codex_wire(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-sp-state-"))
        root = self._make_repo(canonical=True)
        try:
            # Record APPROVE for the exact path-set fingerprint.
            fp = MOD.fingerprint(MOD.l3_paths(root))
            (state).mkdir(parents=True, exist_ok=True)
            (state / "codex-review-log.jsonl").write_text(
                json.dumps(
                    {
                        "session_id": "sp-2",
                        "verdict": "APPROVE",
                        "reviewer_model": "claude-opus-4-8",
                        "fingerprint": fp,
                        "findings": [],
                        "ts": "x",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            obj, _ = self._run(root, _stop_envelope("sp-2", str(root), False), state)
            # Stop-allow on codex is the empty object.
            self.assertNotEqual(obj.get("decision"), "block")
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_noncanonical_allows_on_codex_wire(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-sp-state-"))
        root = self._make_repo(canonical=False)
        try:
            obj, _ = self._run(root, _stop_envelope("sp-3", str(root), False), state)
            self.assertNotEqual(obj.get("decision"), "block")
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_mutation_control_blinded_record_still_blocks(self):
        # Anti-vacuity: if we plant a record with the WRONG fingerprint, the
        # gate must NOT be satisfied (still block). Proves the match has teeth.
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-sp-state-"))
        root = self._make_repo(canonical=True)
        try:
            (state).mkdir(parents=True, exist_ok=True)
            (state / "codex-review-log.jsonl").write_text(
                json.dumps(
                    {
                        "session_id": "sp-4",
                        "verdict": "APPROVE",
                        "fingerprint": "WRONGFINGERPRINT",
                        "ts": "x",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            obj, _ = self._run(root, _stop_envelope("sp-4", str(root), False), state)
            self.assertEqual(obj.get("decision"), "block")
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)


# Post-landing (SENT-CX-D): the gate template lives at its real path — the
# staged overlay copy is gitignored and absent in CI checkouts.
PRE_PUSH_GATE = REPO / "templates" / "codex" / "pre-push-review-gate.sh"


class PrePushGateTests(unittest.TestCase, _GitRepoMixin):
    """Behavioral coverage of the third install surface (the .git/ pre-push
    gate). RED-on-absence: a canonical commit with no review record blocks
    the push; a trailer or a matching sidecar APPROVE clears it."""

    def _make_pushable(self, canonical: bool):
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="w6-push-"))
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
        (root / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True)
        base = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stdout=subprocess.PIPE, check=True,
        ).stdout.decode().strip()
        if canonical:
            f = root / ".claude" / "hooks" / "edited.py"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("# canonical\n", encoding="utf-8")
        else:
            (root / "plain.txt").write_text("x\n", encoding="utf-8")
        return root, base

    def _commit(self, root: Path, msg: str):
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", msg], check=True)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stdout=subprocess.PIPE, check=True,
        ).stdout.decode().strip()

    def _run_gate(self, root: Path, base: str, head: str, state_dir: Path, advisory=False):
        env = dict(os.environ)
        env["CEO_CODEX_REVIEW_STATE_DIR"] = str(state_dir)
        if advisory:
            env["CEO_CODEX_PUSH_GATE_ADVISORY"] = "1"
        stdin = "refs/heads/main %s refs/heads/main %s\n" % (head, base)
        return subprocess.run(
            ["bash", str(PRE_PUSH_GATE), "origin", "https://example/x.git"],
            input=stdin.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(root), env=env, timeout=30,
        )

    def test_canonical_commit_no_record_blocks(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-push-state-"))
        root, base = self._make_pushable(canonical=True)
        try:
            head = self._commit(root, "edit hook")
            proc = self._run_gate(root, base, head, state)
            self.assertEqual(proc.returncode, 1)
            self.assertIn(b"REVIEW GATE", proc.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_noncanonical_commit_passes(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-push-state-"))
        root, base = self._make_pushable(canonical=False)
        try:
            head = self._commit(root, "plain edit")
            proc = self._run_gate(root, base, head, state)
            self.assertEqual(proc.returncode, 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_trailer_clears_gate(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-push-state-"))
        root, base = self._make_pushable(canonical=True)
        try:
            head = self._commit(
                root, "edit hook\n\nPair-Rail-Reviewed: APPROVE claude-opus-4-8"
            )
            proc = self._run_gate(root, base, head, state)
            self.assertEqual(proc.returncode, 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_sidecar_approve_clears_gate(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-push-state-"))
        root, base = self._make_pushable(canonical=True)
        try:
            head = self._commit(root, "edit hook")
            # Fingerprint of the commit's canonical path set (single path).
            fp = MOD.fingerprint([".claude/hooks/edited.py"])
            state.mkdir(parents=True, exist_ok=True)
            (state / "codex-review-log.jsonl").write_text(
                json.dumps(
                    {"session_id": "s", "verdict": "APPROVE", "fingerprint": fp, "ts": "x"}
                ) + "\n",
                encoding="utf-8",
            )
            proc = self._run_gate(root, base, head, state)
            self.assertEqual(proc.returncode, 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)

    def test_advisory_mode_does_not_block(self):
        import tempfile
        state = Path(tempfile.mkdtemp(prefix="w6-push-state-"))
        root, base = self._make_pushable(canonical=True)
        try:
            head = self._commit(root, "edit hook")
            proc = self._run_gate(root, base, head, state, advisory=True)
            self.assertEqual(proc.returncode, 0)
            self.assertIn(b"ADVISORY", proc.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(state, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
