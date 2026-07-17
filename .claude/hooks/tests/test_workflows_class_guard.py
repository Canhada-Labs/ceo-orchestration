"""F3 regression — `.claude/workflows/**/*.js` is guarded as a CLASS.

PLAN-156-FOLLOWUP finding F3 (S270 council live-fire): the guard list carried
the exact path `.claude/workflows/council-audit.js`, so a SIBLING workflow —
which could carry the same external-lane egress — was ordinary-writable. OQ1
(Owner-ratified S270) accepts the cost: authoring any `.claude/workflows/*.js`
becomes a sentinel ceremony.

These tests exercise the classification predicate (the same one the PreToolUse
hook and, post-F5, the push gate's oracle CLI consult), not the hook wire
format — the hook's block/allow plumbing is covered by the existing
canonical-edit suites.

Resolution: `CEO_FU_STAGED_ROOT` (set) → the staged copy under test;
unset → the canonical module (post-ceremony mode).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from typing import Optional

_THIS = Path(__file__).resolve()


def _repo_root() -> Path:
    for cand in [_THIS, *_THIS.parents]:
        if (cand / ".claude" / "hooks").is_dir() and (cand / ".git").exists():
            return cand
    # staged layout: .../staged/root/.claude/hooks/tests/<this>
    return _THIS.parents[4]


_REPO = _repo_root()
_HOOKS = _REPO / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _module_under_test():
    """Load the staged guard when CEO_FU_STAGED_ROOT is set, else canonical."""
    staged_root: Optional[str] = os.environ.get("CEO_FU_STAGED_ROOT")
    if staged_root:
        target = Path(staged_root) / ".claude" / "hooks" / "check_canonical_edit.py"
    else:
        target = _REPO / ".claude" / "hooks" / "check_canonical_edit.py"
    spec = importlib.util.spec_from_file_location("_fu_guard_under_test", target)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError("cannot load guard module at %s" % target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestWorkflowsClassGuard(TestEnvContext):
    """The guard covers the CLASS of workflow scripts, not one instance."""

    def setUp(self) -> None:
        super().setUp()
        self.guard = _module_under_test()

    def _is_canon(self, rel: str) -> bool:
        return bool(self.guard._is_canonical(str(_REPO / rel), _REPO))

    def test_the_original_egress_workflow_stays_guarded(self) -> None:
        self.assertTrue(self._is_canon(".claude/workflows/council-audit.js"))

    def test_sibling_workflow_is_guarded(self) -> None:
        """The F3 gap: a NEW sibling could carry the same egress."""
        self.assertTrue(
            self._is_canon(".claude/workflows/evil-sibling-probe.js"),
            "sibling .claude/workflows/*.js must be guarded as a class — "
            "an exact-path guard protects the instance, not the surface",
        )

    def test_nested_workflow_is_guarded(self) -> None:
        self.assertTrue(
            self._is_canon(".claude/workflows/sub/nested-probe.js"),
            "`**` must cover subdirectories — a nested workflow is the same class",
        )

    def test_command_trigger_stays_guarded(self) -> None:
        self.assertTrue(self._is_canon(".claude/commands/council.md"))

    def test_scope_stays_minimal_non_js_sibling_not_guarded(self) -> None:
        """The glob must not over-reach: docs beside the workflows stay free."""
        self.assertFalse(
            self._is_canon(".claude/workflows/README.md"),
            "the class is *.js (executable egress-bearing surface), not the whole dir",
        )

    def test_unrelated_path_not_guarded(self) -> None:
        self.assertFalse(self._is_canon("tmp/fu-not-canonical-probe.txt"))


if __name__ == "__main__":
    unittest.main()
