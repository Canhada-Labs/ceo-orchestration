"""PLAN-156-FOLLOWUP F5 (consensus C2, unanimous) — fingerprint PARITY between
the grok pre-push review gate and the Stop-review recorder.

## The bug class this pins shut

Two surfaces claim "this push was cross-model reviewed" by hashing a path
set — the recorder (``check_codex_stop_review.py``: aggregate working-tree
set classified by the fine ``check_canonical_edit._is_canonical``) and the
grok push gate (``templates/grok/pre-push-review-gate.sh``). S270 found the
gate hashed COARSE first-segment paths PER-COMMIT — two independent break
axes (classifier + granularity), so sidecar acceptance path (b) could never
match a recorder-written record. The C2 fix:

- (b) ONE oracle: the gate shells out to
  ``python3 check_canonical_edit.py --is-canonical`` — no bash glob-list
  re-implementation (that IS the drift class);
- (a) both sides align UP to the fine set — never down to coarse
  (coarse fingerprints are collision-prone → review-reuse bypass, and
  coarse UNDER-triggers on the egress/disarm surfaces ``templates/**``,
  ``.grok/**``, ``.codex/**``, ``AGENTS.md``);
- (c) the gate aggregates the WHOLE pushed range into one fingerprint
  (matching the recorder's aggregate) — proven here on a MULTI-COMMIT push;
- (d) oracle failure → coarse fallback = over-trigger = fail-CLOSED
  (a broken oracle can only demand MORE review, never wave a touch through).

## Which copy is under test

Per the PLAN-156-FOLLOWUP staging protocol, files under test resolve
through ``CEO_FU_STAGED_ROOT`` (default
``.claude/plans/PLAN-156-FOLLOWUP/staged/root``) and fall back to the
CANONICAL path when no staged copy exists (post-ceremony canonical mode):

- oracle ``check_canonical_edit.py`` — STAGED (canonical + ``_KERNEL_PATHS``;
  lands via ceremony);
- gate ``templates/grok/pre-push-review-gate.sh`` — edited DIRECTLY
  (verified unguarded: the fine set covers only ``templates/settings/*``);
- recorder ``check_codex_stop_review.py`` — UNCHANGED by F5 (it already
  imports ``_is_canonical`` in-process); imported live for its
  ``l3_paths``/``fingerprint`` pipeline.

Scratch git repos are built in the OS temp dir (via TestEnvContext's
isolated tmp tree); the real HOME is never touched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    """Walk up to the real repo (marked by .git).

    A fixed parent-count walk-up breaks when this file runs from the
    PRE-CEREMONY staged pack (`.../staged/root/.claude/scripts/tests/`): it
    would name `staged/root` the repo, and every "canonical" fallback would
    resolve back inside the pack (a file the pack does not carry then raises
    FileNotFoundError). Anchor on `.git` so both layouts — staged and
    post-ceremony canonical — resolve the same real repo.
    """
    for cand in [start, *start.parents]:
        if (cand / ".git").exists():
            return cand
    return start.parent.parent.parent  # pragma: no cover — legacy fallback


_REPO_ROOT = _find_repo_root(_TESTS_DIR)
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_FP_RE = re.compile(r"aggregate path-set fingerprint: ([0-9a-f]{64})")


def _staged_root() -> Path:
    return Path(
        os.environ.get("CEO_FU_STAGED_ROOT")
        or str(_REPO_ROOT / ".claude" / "plans" / "PLAN-156-FOLLOWUP" / "staged" / "root")
    )


def _resolve_under_test(rel: str) -> Path:
    """Staged copy when present, else the canonical file (post-ceremony)."""
    staged = _staged_root() / rel
    if staged.is_file():
        return staged
    return _REPO_ROOT / rel


_ORACLE = _resolve_under_test(".claude/hooks/check_canonical_edit.py")
_GATE = _resolve_under_test("templates/grok/pre-push-review-gate.sh")
_RECORDER = _resolve_under_test(".claude/hooks/check_codex_stop_review.py")


def _load_module(name: str, path: Path):
    # dont_write_bytecode: never drop a __pycache__ into the STAGED tree
    # (the ceremony copies staged/root/** verbatim over canonical paths).
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        assert spec is not None and spec.loader is not None, path
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.dont_write_bytecode = prev


# ---------------------------------------------------------------------------
# COARSE legacy classifier mirror — TEST-ONLY documentation of the gate's
# fail-CLOSED fallback (and of the pre-F5 behavior), used exclusively to
# ENUMERATE the coverage delta. This is not a production re-implementation:
# the production gate consults the oracle; its own bash coarse list survives
# only as the oracle-failure fallback (C2(d)).
# ---------------------------------------------------------------------------

def _parse_gate_coarse_prefixes() -> Dict[str, frozenset]:
    """Derive the coarse classifier's sets FROM THE GATE FILE itself.

    A hardcoded mirror is a second source of truth — i.e. the very drift class
    F5 exists to kill (pair-rail R2 caught the gate's list silently missing the
    egress surfaces while a stale mirror here still "passed"). Parse the two
    `case` arms of `_is_canonical_path` instead, so the superset test below
    compares the ORACLE against what the gate ACTUALLY ships.
    """
    text = _GATE.read_text(encoding="utf-8")
    body = re.search(
        r"_is_canonical_path\(\)\s*\{.*?case \"\$1\" in(.*?)esac", text, re.S
    )
    assert body, "could not locate _is_canonical_path's case block in %s" % _GATE
    prefixes, files = set(), set()
    for arm in re.findall(r"^\s*([^)\n]+)\)\s*return 0", body.group(1), re.M):
        for pat in arm.split("|"):
            pat = pat.strip()
            if pat.endswith("/*"):
                prefixes.add(pat[:-2])
            elif pat and "*" not in pat:
                files.add(pat)
    assert prefixes, "no coarse prefixes parsed from the gate"
    return {"prefixes": frozenset(prefixes), "files": frozenset(files)}


_COARSE = _parse_gate_coarse_prefixes()
_COARSE_PREFIXES = _COARSE["prefixes"]
_COARSE_FILES = _COARSE["files"]


def _coarse_is_canonical(rel_path: str) -> bool:
    if rel_path in _COARSE_FILES:
        return True
    return rel_path.split("/", 1)[0] in _COARSE_PREFIXES


class _ScratchRepo:
    """Minimal multi-commit push scenario in an OS-temp scratch git repo."""

    # canonical (fine set) — spread across DIFFERENT commits on purpose
    CANONICAL = [
        ".claude/hooks/foo.py",              # commit 1
        "PROTOCOL.md",                       # commit 2
        "AGENTS.md",                         # commit 3 (fine-only gain)
        ".grok/config.toml",                 # commit 3 (fine-only gain)
        "templates/settings/settings.base.json",  # commit 3 (fine-only gain)
    ]
    # non-canonical (fine set); the plans note is COARSE-canonical → the
    # exact F5 divergence path (.claude first segment, no guard match)
    NON_CANONICAL = [
        "src/app.py",                        # commit 1
        ".claude/plans/PLAN-001-note.md",    # commit 2 (coarse-only)
        "README.md",                         # commit 2
    ]
    COMMITS = [
        [".claude/hooks/foo.py", "src/app.py"],
        ["PROTOCOL.md", ".claude/plans/PLAN-001-note.md", "README.md"],
        ["AGENTS.md", ".grok/config.toml", "templates/settings/settings.base.json"],
    ]

    def __init__(self, root: Path) -> None:
        self.root = root

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.root),
             "-c", "user.name=f5-test", "-c", "user.email=f5@test.invalid"]
            + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        assert proc.returncode == 0, (args, proc.stderr.decode("utf-8", "replace"))
        return proc.stdout.decode("utf-8", "replace").strip()

    def init_base(self) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        self._git("init", "-q")
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        self._git("add", "base.txt")
        self._git("commit", "-q", "-m", "base")
        return self._git("rev-parse", "HEAD")

    def write_working_tree(self) -> None:
        for rel in self.CANONICAL + self.NON_CANONICAL:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("content for %s\n" % rel, encoding="utf-8")

    def commit_in_three(self, trailer: bool = False) -> List[str]:
        shas: List[str] = []
        for i, files in enumerate(self.COMMITS, start=1):
            self._git("add", *files)
            msg = "commit %d" % i
            if trailer:
                msg += "\n\nPair-Rail-Reviewed: APPROVE"
            self._git("commit", "-q", "-m", msg)
            shas.append(self._git("rev-parse", "HEAD"))
        return shas


class FingerprintParityTest(TestEnvContext):
    """Multi-commit recorder↔gate fingerprint parity + fail-closed fallback."""

    def setUp(self) -> None:
        super().setUp()
        self.assertTrue(_ORACLE.is_file(), "oracle under test missing: %s" % _ORACLE)
        self.assertTrue(_GATE.is_file(), "gate under test missing: %s" % _GATE)
        self.scratch = self._tmp_root / "scratch-repo"
        self.state_dir = self._tmp_root / "review-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.repo = _ScratchRepo(self.scratch)
        self.base_sha = self.repo.init_base()
        self.repo.write_working_tree()
        # Recorder-side fingerprint at "Stop time": the working tree carries
        # the changes (untracked), exactly like a session pre-commit. Force
        # the recorder's `import check_canonical_edit` to resolve to the
        # oracle copy under test (mock.patch.dict → no sys.modules leak).
        oracle_mod = _load_module("_f5_oracle_under_test", _ORACLE)
        recorder_mod = _load_module("_f5_recorder", _RECORDER)
        with mock.patch.dict(sys.modules, {"check_canonical_edit": oracle_mod}):
            l3 = recorder_mod.l3_paths(self.scratch)
            self.recorder_fp = recorder_mod.fingerprint(l3)
        self.assertEqual(
            sorted(_ScratchRepo.CANONICAL), l3,
            "recorder-side fine classification drifted from the fixture",
        )
        self.fingerprint_fn = recorder_mod.fingerprint
        # Now commit the SAME set as a MULTI-COMMIT push (C2(c)).
        self.commit_shas = self.repo.commit_in_three()
        self.head_sha = self.commit_shas[-1]

    def _gate_env(self, oracle: Optional[Path] = None) -> Dict[str, str]:
        env = dict(os.environ)  # HOME already isolated by TestEnvContext
        env["CEO_GROK_REVIEW_STATE_DIR"] = str(self.state_dir)
        env["CEO_CANONICAL_ORACLE"] = str(oracle if oracle is not None else _ORACLE)
        env.pop("CEO_GROK_PUSH_GATE", None)
        env.pop("CEO_GROK_PUSH_GATE_ADVISORY", None)
        return env

    def _run_gate(
        self, remote_sha: str, local_sha: str, oracle: Optional[Path] = None
    ) -> "subprocess.CompletedProcess[bytes]":
        stdin_line = "refs/heads/main %s refs/heads/main %s\n" % (local_sha, remote_sha)
        return subprocess.run(
            ["bash", str(_GATE), "origin", "file:///dev/null"],
            input=stdin_line.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.scratch),
            env=self._gate_env(oracle=oracle),
            timeout=60,
        )

    def test_reverted_canonical_edit_in_range_still_gates(self) -> None:
        """A canonical edit REVERTED later in the same push must still gate.

        Pair-rail R3 (S272): the gate classified the ENDPOINT diff
        (`git diff remote..local`) — the NET effect of the push. An edit+revert
        range nets to nothing, so the gate saw an empty canonical set and exited
        0, while the unreviewed canonical edit still reached the remote inside
        the intermediate commit (a revert-of-the-revert or a cherry-pick
        resurrects it, forever unreviewed). The gate now unions the paths of
        EVERY pushed commit.
        """
        scratch2 = self._tmp_root / "revert-repo"
        repo2 = _ScratchRepo(scratch2)
        base2 = repo2.init_base()

        canonical_rel = ".claude/hooks/reverted_probe.py"
        target = scratch2 / canonical_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# unreviewed canonical edit\n", encoding="utf-8")
        repo2._git("add", canonical_rel)
        repo2._git("commit", "-q", "-m", "edit canonical")

        repo2._git("rm", "-q", canonical_rel)
        repo2._git("commit", "-q", "-m", "revert the canonical edit")
        head2 = repo2._git("rev-parse", "HEAD")

        net = repo2._git("diff", "--name-only", "%s..%s" % (base2, head2))
        self.assertEqual(
            "", net.strip(),
            "fixture precondition: the endpoint diff must be EMPTY — that is "
            "the blind spot under test",
        )

        stdin_line = "refs/heads/main %s refs/heads/main %s\n" % (head2, base2)
        proc = subprocess.run(
            ["bash", str(_GATE), "origin", "file:///dev/null"],
            input=stdin_line.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(scratch2),
            env=self._gate_env(),
            timeout=60,
        )
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertNotEqual(
            0, proc.returncode,
            "gate exited 0 on a push whose intermediate commit carries an "
            "UNREVIEWED canonical edit (endpoint-diff blind spot, R3):\n" + stderr,
        )
        self.assertIn(canonical_rel, stderr)

    def test_new_branch_first_push_still_gates(self) -> None:
        """A brand-new branch's FIRST push must still classify its commits.

        Pair-rail R4 (S272): the new-branch arm used
        `git rev-list <local> --not --all`, and `--all` includes the local ref
        being pushed (it points AT <local>), so the range subtracted itself and
        the commit list was EMPTY. Since the per-commit union (R3) is now the
        only source of classified paths, a first push carrying canonical edits
        sailed through. The arm now subtracts `--remotes` — what the remote
        already has — which is the question the gate actually asks.
        """
        scratch3 = self._tmp_root / "newbranch-repo"
        repo3 = _ScratchRepo(scratch3)
        repo3.init_base()

        # A feature branch with a canonical edit, never pushed anywhere.
        repo3._git("checkout", "-q", "-b", "feature/canonical-touch")
        canonical_rel = ".claude/hooks/new_branch_probe.py"
        target = scratch3 / canonical_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# unreviewed canonical edit on a new branch\n",
                          encoding="utf-8")
        repo3._git("add", canonical_rel)
        repo3._git("commit", "-q", "-m", "canonical edit on a fresh branch")
        head3 = repo3._git("rev-parse", "HEAD")

        # remote_sha = 0{40} is git's "this ref does not exist on the remote".
        stdin_line = "refs/heads/feature/canonical-touch %s refs/heads/feature/canonical-touch %s\n" % (
            head3, "0" * 40,
        )
        proc = subprocess.run(
            ["bash", str(_GATE), "origin", "file:///dev/null"],
            input=stdin_line.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(scratch3),
            env=self._gate_env(),
            timeout=60,
        )
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertNotEqual(
            0, proc.returncode,
            "gate exited 0 on the FIRST push of a branch carrying an unreviewed "
            "canonical edit (the --not --all self-subtraction, R4):\n" + stderr,
        )
        self.assertIn(canonical_rel, stderr)

    def test_root_commit_canonical_paths_are_classified(self) -> None:
        """A ROOT commit (no parent) that ADDS canonical files must gate.

        Pair-rail R5 (S272): `git diff-tree` emits NOTHING for a root commit
        unless `--root` is passed — so a brand-new repo whose FIRST commit adds
        canonical files classified an empty set and the push passed.
        """
        scratch4 = self._tmp_root / "rootcommit-repo"
        scratch4.mkdir(parents=True, exist_ok=True)
        repo4 = _ScratchRepo(scratch4)
        repo4._git_init_only = True
        subprocess.run(["git", "init", "-q"], cwd=str(scratch4), timeout=30, check=True)

        canonical_rel = ".claude/hooks/root_probe.py"
        target = scratch4 / canonical_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# canonical file added by the ROOT commit\n", encoding="utf-8")
        repo4._git("add", canonical_rel)
        repo4._git("commit", "-q", "-m", "root commit adds a canonical file")
        head4 = repo4._git("rev-parse", "HEAD")

        stdin_line = "refs/heads/main %s refs/heads/main %s\n" % (head4, "0" * 40)
        proc = subprocess.run(
            ["bash", str(_GATE), "origin", "file:///dev/null"],
            input=stdin_line.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(scratch4),
            env=self._gate_env(),
            timeout=60,
        )
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertNotEqual(
            0, proc.returncode,
            "gate exited 0 on a push whose ROOT commit adds canonical files "
            "(diff-tree without --root emits nothing, R5):\n" + stderr,
        )
        self.assertIn(canonical_rel, stderr)

    def test_multi_commit_parity_and_sidecar_reuse(self) -> None:
        """AC: gate aggregate fingerprint == recorder fingerprint over a
        3-commit push, and a recorder-keyed APPROVE record clears the gate."""
        # Phase 1 — RED without any record; extract the gate's fingerprint.
        proc = self._run_gate(self.base_sha, self.head_sha)
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 1, stderr)
        m = _FP_RE.search(stderr)
        self.assertIsNotNone(m, "gate did not print an aggregate fingerprint:\n" + stderr)
        gate_fp = m.group(1)  # type: ignore[union-attr]
        self.assertEqual(
            self.recorder_fp, gate_fp,
            "PARITY BROKEN: recorder fp != gate aggregate fp\n" + stderr,
        )
        # The fine-only gains must be in the gate's reported canonical set.
        for covered in ("AGENTS.md", ".grok/config.toml",
                        "templates/settings/settings.base.json"):
            self.assertIn(covered, stderr)
        # The coarse-only path must NOT be gated (fine says non-canonical).
        self.assertNotIn(".claude/plans/PLAN-001-note.md", stderr)

        # Phase 2 — a sidecar APPROVE record keyed by the RECORDER's
        # fingerprint (the real cross-process reuse loop) clears the push.
        record = {
            "session_id": "f5-parity",
            "fingerprint": self.recorder_fp,
            "verdict": "APPROVE",
        }
        log = self.state_dir / "grok-review-log.jsonl"
        log.write_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        proc2 = self._run_gate(self.base_sha, self.head_sha)
        self.assertEqual(
            proc2.returncode, 0,
            "recorder-keyed APPROVE did not clear the gate:\n"
            + proc2.stderr.decode("utf-8", "replace"),
        )

    def test_aggregate_is_not_any_per_commit_fingerprint(self) -> None:
        """Documents the granularity half of C2(c): the pre-F5 per-commit
        fingerprints can never equal the aggregate on a multi-commit push."""
        per_commit_fps = []
        for sha, files in zip(self.commit_shas, _ScratchRepo.COMMITS):
            canon = [f for f in files if f in _ScratchRepo.CANONICAL]
            if canon:
                per_commit_fps.append(self.fingerprint_fn(canon))
        self.assertGreaterEqual(
            len(per_commit_fps), 2,
            "fixture must spread canonical paths across >=2 commits",
        )
        for fp in per_commit_fps:
            self.assertNotEqual(fp, self.recorder_fp)

    def test_trailer_path_still_clears(self) -> None:
        """Acceptance path (a) survives the rewrite: APPROVE trailers on
        every canonical-touching commit clear the push with no sidecar."""
        repo2 = _ScratchRepo(self._tmp_root / "scratch-repo-trailers")
        base = repo2.init_base()
        repo2.write_working_tree()
        shas = repo2.commit_in_three(trailer=True)
        stdin_line = "refs/heads/main %s refs/heads/main %s\n" % (shas[-1], base)
        proc = subprocess.run(
            ["bash", str(_GATE), "origin", "file:///dev/null"],
            input=stdin_line.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(repo2.root),
            env=self._gate_env(),
            timeout=60,
        )
        self.assertEqual(
            proc.returncode, 0, proc.stderr.decode("utf-8", "replace")
        )

    def test_oracle_failure_falls_back_coarse_fail_closed(self) -> None:
        """C2(d): a broken oracle degrades to the coarse OVER-triggering
        classifier — and a recorder-keyed APPROVE must NOT clear it (the
        coarse fingerprint intentionally cannot match; degraded mode
        demands trailers, never grants a bypass)."""
        record = {
            "session_id": "f5-parity",
            "fingerprint": self.recorder_fp,
            "verdict": "APPROVE",
        }
        (self.state_dir / "grok-review-log.jsonl").write_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        proc = self._run_gate(
            self.base_sha, self.head_sha,
            oracle=self._tmp_root / "no-such-oracle.py",
        )
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertIn("COARSE", stderr)
        self.assertEqual(proc.returncode, 1, stderr)


class OracleCliContractTest(TestEnvContext):
    """Subprocess contract of the oracle CLI (import-safety AC + delta)."""

    def _run_oracle(
        self, args: List[str], cwd: Path, project_dir: Path,
        stdin: Optional[str] = None,
    ) -> "subprocess.CompletedProcess[bytes]":
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        return subprocess.run(
            [sys.executable, str(_ORACLE), "--is-canonical"] + args,
            input=(stdin.encode("utf-8") if stdin is not None else None),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            env=env,
            timeout=60,
        )

    def test_import_safe_subprocess_from_repo_root(self) -> None:
        """AC: the STAGED copy runs as a script from repo root (no _lib
        sibling in the staged dir — module import must survive that)."""
        proc = self._run_oracle(["PROTOCOL.md"], cwd=_REPO_ROOT, project_dir=_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(
            proc.stdout.decode("utf-8"), "PROTOCOL.md\t1\n"
        )

    def test_stdin_mode_and_usage_exit(self) -> None:
        proc = self._run_oracle(
            ["-"], cwd=_REPO_ROOT, project_dir=_REPO_ROOT,
            stdin="AGENTS.md\nREADME.md\n",
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(
            proc.stdout.decode("utf-8"), "AGENTS.md\t1\nREADME.md\t0\n"
        )
        empty = self._run_oracle([], cwd=_REPO_ROOT, project_dir=_REPO_ROOT)
        self.assertEqual(empty.returncode, 2)
        self.assertEqual(empty.stdout, b"")

    def test_coverage_delta_fine_vs_coarse(self) -> None:
        """Documents the C2(e) delta (enumerated in
        .claude/plans/PLAN-156-FOLLOWUP/staged/coverage-delta-f5.md):
        fine-set GAINS on the egress/disarm surfaces the coarse classifier
        misses, and fine-set LOSSES (coarse over-triggers) on paths with a
        canonical first segment but no guard match."""
        # After the R2 superset fix these are covered by BOTH sets — the
        # fail-OPEN gap is closed. They stay in the fixture as a REGRESSION
        # pin: the fine set must still cover them (see also the superset
        # invariant test below, which pins the coarse side).
        fine_covered = [
            "templates/settings/settings.base.json",
            ".grok/config.toml",
            ".codex/hooks.json",
            "AGENTS.md",
        ]
        lost = [
            ".claude/plans/PLAN-001-note.md",
            "scripts/notes.txt",
            ".github/README.md",
        ]
        proc = self._run_oracle(
            fine_covered + lost, cwd=_REPO_ROOT, project_dir=_REPO_ROOT
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        flags: Dict[str, str] = {}
        for line in proc.stdout.decode("utf-8").splitlines():
            path, _, flag = line.rpartition("\t")
            flags[path] = flag
        for p in fine_covered:
            self.assertEqual(flags.get(p), "1", "fine set must cover %s" % p)
            self.assertTrue(
                _coarse_is_canonical(p),
                "%s must ALSO be coarse-canonical — the degraded fallback has "
                "to be a SUPERSET of the fine set, or a degraded push touching "
                "only this surface produces an empty set and exits 0 "
                "(fail-OPEN; pair-rail R2)" % p,
            )
        for p in lost:
            self.assertEqual(flags.get(p), "0", "fine set must NOT cover %s" % p)
            self.assertTrue(
                _coarse_is_canonical(p),
                "%s should document a LOSS (coarse over-triggered)" % p,
            )


class CoarseSupersetInvariantTest(TestEnvContext):
    """The degraded fallback must be a SUPERSET of the fine oracle's segments.

    "Over-triggers = fail-CLOSED" is a claim about SET CONTAINMENT, not a
    slogan. Pair-rail R2 (S272) found it false: the coarse list omitted
    `templates/`, `.grok/`, `.codex/`, `AGENTS.md` and `requirements.toml`, so
    a degraded push touching only those classified NOTHING as canonical and the
    gate exited 0 — an under-trigger on the egress + kill-switch + distribution
    surfaces. This test pins the invariant so the next `_CANONICAL_GUARDS`
    addition cannot silently reopen the hole.
    """

    def test_every_oracle_first_segment_is_coarse_canonical(self) -> None:
        guard = _load_module("_f5_oracle_superset", _ORACLE)
        segments = set()
        for pattern in guard._CANONICAL_GUARDS:
            head = pattern.split("/", 1)[0]
            if "*" in head:  # a leading wildcard would make containment vacuous
                self.fail("guard pattern with a wildcard first segment: %s" % pattern)
            segments.add(head if "/" in pattern else pattern)
        self.assertTrue(segments, "oracle guard list is empty — cannot verify")
        missing = sorted(
            seg for seg in segments
            if not _coarse_is_canonical(seg if "." in seg and "/" not in seg
                                        else seg + "/probe")
        )
        self.assertEqual(
            [], missing,
            "coarse degraded fallback does NOT cover these oracle-guarded "
            "first segments: %s. A degraded push touching only one of them "
            "yields an EMPTY canonical set and the gate exits 0 (fail-OPEN). "
            "Add the segment to _is_canonical_path in "
            "templates/grok/pre-push-review-gate.sh." % missing,
        )


if __name__ == "__main__":
    unittest.main()
