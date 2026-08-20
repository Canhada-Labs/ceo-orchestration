"""PLAN-179 rail round-7 [P2] — sidecar reader/writer override parity.

The class: `statusline-ceo.py` (the WRITER) expands `~` in
`CEO_STATUSLINE_SIDECAR` and REJECTS symlink/traversal overrides, falling
back to the default path. The reader in `check_precompact_continuity.py`
used to take the override literally — so with `~/...` telemetry silently
vanished, and a symlink/traversal override the writer refused could still
be READ, accepting crafted data the writer never wrote.

These tests pin the parity: same expansion, same rejection, same fallback.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_THIS = Path(__file__).resolve()
_repo_root = None
for parent in _THIS.parents:
    if (parent / ".claude" / "hooks" / "_lib").is_dir() and (
        parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = parent
        break
assert _repo_root is not None, "could not locate repo root from test path"
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_CANONICAL = _LIVE_HOOKS / "check_precompact_continuity.py"
_STAGED = (
    _repo_root / ".claude" / "plans" / "PLAN-179" / "staged-w01"
    / ".claude" / "hooks" / "check_precompact_continuity.py"
)
# Marker unique to the round-7 cure (the reader-side mirror of the writer's
# override validator).
_MARKER = "_sidecar_override_safe"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "check_precompact_continuity with the round-7 reader parity not "
        "found in canonical (%s) or staged (%s)" % (canonical, staged)
    )


_HOOK_PATH = _pick(_CANONICAL, _STAGED, _MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "_plan179_precompact_under_test", str(_HOOK_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


_hook = _load_hook()

_SID = "sess-parity-1"


class SidecarParityBase(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.home = Path(self.project_dir) / "home"
        self.audit_dir = Path(self.project_dir) / "audit"
        (self.audit_dir / "state").mkdir(parents=True)
        self.home.mkdir()
        self.cwd = str(Path(self.project_dir) / "repo")
        Path(self.cwd).mkdir()

    def _snap(self, pct):
        return json.dumps(
            {"session_id": _SID, "project_dir": self.cwd, "context_pct": pct}
        )

    def _write_default(self, pct):
        p = self.audit_dir / "state" / "statusline-snapshot.json"
        p.write_text(self._snap(pct), encoding="utf-8")
        return p

    def _read(self, override):
        env = {
            "HOME": str(self.home),
            "CEO_AUDIT_LOG_DIR": str(self.audit_dir),
            "CEO_STATUSLINE_SIDECAR": override,
        }
        with mock.patch.dict(os.environ, env, clear=False):
            return _hook._context_pct_from_sidecar(_SID, self.cwd)


class TestOverrideParityWithWriter(SidecarParityBase):
    def test_plain_absolute_override_is_read(self):
        target = self.home / "side.json"
        target.write_text(self._snap(77), encoding="utf-8")
        self._write_default(33)
        self.assertEqual(self._read(str(target)), 77)

    def test_tilde_override_is_expanded_like_the_writer(self):
        """`~/...` must resolve against $HOME — the literal reading made
        adopter telemetry silently disappear."""
        target = self.home / "side.json"
        target.write_text(self._snap(61), encoding="utf-8")
        self.assertEqual(self._read("~/side.json"), 61)

    def test_symlink_override_falls_back_to_default(self):
        """The writer REJECTS a symlink override and writes to the default;
        reading the symlink would accept crafted data the writer never
        wrote. The reader must land on the default too."""
        crafted = self.home / "crafted.json"
        crafted.write_text(self._snap(99), encoding="utf-8")
        link = self.home / "link.json"
        os.symlink(str(crafted), str(link))
        self._write_default(33)
        self.assertEqual(self._read(str(link)), 33)

    def test_traversal_override_falls_back_to_default(self):
        traversal = str(self.home / ".." / "home" / "side.json")
        (self.home / "side.json").write_text(self._snap(88), encoding="utf-8")
        self._write_default(33)
        self.assertEqual(self._read(traversal), 33)

    def test_subdirectory_cwd_matches_project_root(self):
        """Rail round-8 [P2]: the writer stores the project ROOT; a hook cwd
        INSIDE that root (CwdChanged) must still match the identity gate."""
        sub = Path(self.cwd) / "src" / "deep"
        sub.mkdir(parents=True)
        target = self.home / "side.json"
        target.write_text(self._snap(42), encoding="utf-8")
        env = {
            "HOME": str(self.home),
            "CEO_AUDIT_LOG_DIR": str(self.audit_dir),
            "CEO_STATUSLINE_SIDECAR": str(target),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            self.assertEqual(
                _hook._context_pct_from_sidecar(_SID, str(sub)), 42
            )

    def test_foreign_project_root_is_still_rejected(self):
        other = Path(self.project_dir) / "other-repo"
        other.mkdir()
        target = self.home / "side.json"
        target.write_text(self._snap(42), encoding="utf-8")
        env = {
            "HOME": str(self.home),
            "CEO_AUDIT_LOG_DIR": str(self.audit_dir),
            "CEO_STATUSLINE_SIDECAR": str(target),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            self.assertIsNone(
                _hook._context_pct_from_sidecar(_SID, str(other))
            )

    def test_symlinked_parent_falls_back_to_default(self):
        real_dir = self.home / "real"
        real_dir.mkdir()
        (real_dir / "side.json").write_text(self._snap(55), encoding="utf-8")
        link_dir = self.home / "linkdir"
        os.symlink(str(real_dir), str(link_dir))
        self._write_default(33)
        self.assertEqual(self._read(str(link_dir / "side.json")), 33)


class TestProjectRootResolver(SidecarParityBase):
    """Rail round-9 [P2]: every path the hook derives is anchored at the
    project ROOT, resolved once in gate() by `_resolve_project_root`."""

    def test_subdir_resolves_to_nearest_claude_ancestor(self):
        root = Path(self.cwd)
        (root / ".claude").mkdir()
        sub = root / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(
            _hook._resolve_project_root(str(sub)), str(root.resolve())
        )

    def test_walkup_stops_at_the_isolated_project_root(self):
        """TestEnvContext plants `.claude/` at project_dir — the walk-up
        from any bare subtree must stop THERE, never escape the isolated
        environment toward the real $HOME."""
        bare = Path(self.project_dir) / "bare" / "tree"
        bare.mkdir(parents=True)
        self.assertEqual(
            _hook._resolve_project_root(str(bare)),
            str(Path(self.project_dir).resolve()),
        )


if __name__ == "__main__":
    unittest.main()
