"""PLAN-160 Wave 1 — per-finding verification instruments for the S276
council findings on ``check_canonical_edit.py`` (A / B / C / D).

This file is a VERIFICATION INSTRUMENT, not a fix. It must keep the suite
GREEN on HEAD while documenting the real defects via
``xfail(strict=True)`` markers, so that the Wave-2 fix is FORCED to flip
them (strict xfail turns an unexpected pass into a failure).

## Feature-detect contract (Wave 2 depends on this — do not change)

The fixed hook will contain module-level constants ``PLAN160_FIX_A``,
``PLAN160_FIX_C``, ``PLAN160_FIX_D``. This file reads the SOURCE of the
hook-under-test and derives per-finding flags::

    FIXED_A = "PLAN160_FIX_A" in source   # etc.

Hook-under-test = env ``PLAN160_HOOK_PATH`` (absolute path) when set,
else the canonical ``.claude/hooks/check_canonical_edit.py``. Every
subprocess invocation AND every in-process import in this file targets
that path, so Wave 2 can point the SAME tests at a staged copy.

## Instruments

* **A — gate-bypass, multi-candidate** (``FindingAGateBypassTest``):
  ``main()`` (L1367-1374 on HEAD) breaks on the FIRST canonical
  candidate and gates ONLY that one path. A write-shaped MCP event
  carrying two canonical paths — one sentinel-GRANTED, one UNGRANTED —
  is ALLOWED on HEAD when the granted path comes first: the ungranted
  path rides along. Driven END-TO-END through ``main()`` via the
  subprocess harness (the in-process ``_LayerABase._decide`` helper in
  ``test_check_canonical_edit_mcp.py`` re-implements the same break and
  would be a false-green).

  Empirical note (probed on HEAD, this instrument's own dry run): with
  the UNGRANTED path first, HEAD *blocks* — the break happens to select
  the offender. That order therefore CANNOT carry a strict xfail (it
  would XPASS); it is kept as an always-pass control pinning the
  post-fix contract, and order-independence is enforced by the
  both-orders xfail repro below.

* **B — cache blast radius** (``FindingBCacheBlastRadiusTest``):
  characterization, PASSES on HEAD, no xfail. Behavioral, not
  stat-introspective: grant → allow, revoke the Scope on disk, fresh
  subprocess → block. Proves the sentinel-verify cache's blast radius
  is one invocation (fresh process per hook call).

* **C — dead fail-open except in ``decide()``** (``FindingCDeadnessTest``):
  a deadness PROPERTY (passes on HEAD) proving the ``except (ValueError,
  OSError) -> allow`` at decide() L1136-1139 is unreachable except under
  same-process TOCTOU, plus a forced-branch white-box test (xfail-strict
  on HEAD) asserting the STILL-UNSHIPPED defense-in-depth: a resolve
  fault after ``_is_canonical`` confirmed canonical must BLOCK with
  ``canonical_edit_hook_fault``.

* **D — relative-path bypass** (``FindingDRelativePathTest``):
  a RELATIVE ``file_path`` for a canonical file, hook invoked with
  ``cwd`` != ``CLAUDE_PROJECT_DIR`` (subprocess ``cwd=``, never
  ``os.chdir``): ``_is_canonical`` resolves against cwd, lands outside
  the repo root, returns False → allow on HEAD. Post-fix: treated as
  canonical → block. Twin absolute-path control passes always.
  NOTE: D's input makes ``_is_canonical`` return False, so C's except
  is NEVER reached on this path — D input must not be used to verify C.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

# Post-canonical-promotion layout: parents[0]=tests/ [1]=hooks/
# [2]=.claude/ [3]=repo root. Root conftest already seeds sys.path;
# the explicit insert keeps `python3 -m unittest` discovery working.
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# ---------------------------------------------------------------------------
# Feature-detect contract (PLAN-160): hook-under-test + per-finding flags.
# ---------------------------------------------------------------------------
_DEFAULT_HOOK_PATH = _HOOKS_DIR / "check_canonical_edit.py"
_HOOK_PATH = Path(
    os.environ.get("PLAN160_HOOK_PATH") or str(_DEFAULT_HOOK_PATH)
).resolve()
_HOOK_SOURCE = _HOOK_PATH.read_text(encoding="utf-8")

FIXED_A = "PLAN160_FIX_A" in _HOOK_SOURCE
FIXED_C = "PLAN160_FIX_C" in _HOOK_SOURCE
FIXED_D = "PLAN160_FIX_D" in _HOOK_SOURCE

_XFAIL_A = pytest.mark.xfail(
    condition=not FIXED_A,
    reason=(
        "PLAN-160 finding A: defect present on HEAD; flips after Wave-2 fix"
    ),
    strict=True,
)
_XFAIL_C = pytest.mark.xfail(
    condition=not FIXED_C,
    reason=(
        "PLAN-160 finding C: defect present on HEAD; flips after Wave-2 fix"
    ),
    strict=True,
)
_XFAIL_D = pytest.mark.xfail(
    condition=not FIXED_D,
    reason=(
        "PLAN-160 finding D: defect present on HEAD; flips after Wave-2 fix"
    ),
    strict=True,
)


# In-process (white-box) import of the hook-under-test. Loaded under a
# UNIQUE module name so the canonical ``check_canonical_edit`` import used
# by sibling test files is never clobbered (xdist-safe: per-process cache;
# monkeypatches in tests use mock.patch.object context managers which
# restore on exit, so the shared module object stays pristine between
# tests).
_HOOK_MODULE_CACHE: Dict[str, object] = {}


def _load_hook_module():
    key = str(_HOOK_PATH)
    mod = _HOOK_MODULE_CACHE.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "plan160_hook_under_test", str(_HOOK_PATH)
        )
        if spec is None or spec.loader is None:  # pragma: no cover
            raise RuntimeError(
                f"PLAN-160: cannot load hook-under-test at {_HOOK_PATH}"
            )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _HOOK_MODULE_CACHE[key] = mod
    return mod


class _CouncilFindingsBase(TestEnvContext):
    """Shared subprocess harness + fixtures.

    ``_invoke`` mirrors ``test_check_canonical_edit.py:30-56`` exactly
    (CEO_SENTINEL_UNLOCK dual-auth bypass so PLAINTEXT sentinels are
    honored — these tests exercise Approved-By + Scope, not GPG), with
    an optional ``cwd`` for the finding-D repro (subprocess ``cwd=``,
    never ``os.chdir`` — xdist-safe). ``os.environ`` is already isolated
    by ``TestEnvContext.setUp`` (tmp HOME / CLAUDE_PROJECT_DIR /
    CEO_AUDIT_LOG_*), so the child env inherits the isolation.
    """

    def _invoke(
        self,
        payload: dict,
        cwd: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        env = {**os.environ}
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-160-council-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        proc = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=cwd,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _decision(self, payload: dict, cwd: Optional[str] = None) -> dict:
        rc, out, err = self._invoke(payload, cwd=cwd)
        self.assertEqual(rc, 0, msg=f"stdout={out!r} stderr={err!r}")
        return json.loads(out)

    def _make_repo_layout(self) -> Path:
        (self.project_dir / ".claude").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "team.md").write_text(
            "team", encoding="utf-8"
        )
        (self.project_dir / ".claude" / "frontend-team.md").write_text(
            "front", encoding="utf-8"
        )
        return self.project_dir

    def _write_sentinel(
        self,
        plan_id: str,
        scope_paths: list,
        approved_by: str = "@Canhada-Labs deadbeef",
    ) -> Path:
        sentinel_dir = (
            self.project_dir / ".claude" / "plans" / plan_id
            / "architect" / "round-1"
        )
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        scope_block = "\n".join(f"  - {p}" for p in scope_paths)
        body = (
            "---\nplan: " + plan_id
            + "\nround: 1\ntype: architect-sentinel\n---\n\n"
            f"Approved-By: {approved_by}\n"
            "Approved-At: 2026-04-13T15:30:00Z\n"
            "Scope:\n"
            f"{scope_block}\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        return sentinel_dir / "approved.md"

    @staticmethod
    def _mcp_bulk_write_event(paths: list) -> dict:
        """Write-shaped MCP tool call carrying N candidate target paths.

        Shape verified against ``_extract_mcp_target_paths``: the ``path``
        key accepts a LIST of strings (each item becomes one candidate,
        in list order), and ``tool_name`` starting with ``mcp__`` routes
        the event through the Layer-A multi-candidate scan in ``main()``.
        """
        return {
            "hook_event_name": "PreToolUse",
            "session_id": "plan160-w1",
            "tool_name": "mcp__future__bulk_write",
            "tool_input": {"path": list(paths), "content": "x"},
        }


# ===========================================================================
# Finding A — multi-candidate gate bypass (xfail-strict repros + controls)
# ===========================================================================
class FindingAGateBypassTest(_CouncilFindingsBase):
    """Council finding A: ``main()`` breaks on the first canonical
    candidate and gates only it; further canonical candidates ride along
    on that single decision (gate bypass when the first canonical
    candidate is sentinel-granted).
    """

    GRANTED_REL = ".claude/team.md"
    UNGRANTED_REL = ".claude/frontend-team.md"

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()
        self._write_sentinel("PLAN-201", [self.GRANTED_REL])
        self.granted_abs = str(self.project_dir / self.GRANTED_REL)
        self.ungranted_abs = str(self.project_dir / self.UNGRANTED_REL)

    # ---- controls (must PASS on HEAD, no xfail) --------------------------

    def test_a_control_single_granted_allows(self) -> None:
        """Fixture-validity control: single {granted} candidate → allow.

        Guards against the false-repro pitfall where an INVALID sentinel
        fixture makes everything block and the A repro 'passes' for the
        wrong reason.
        """
        d = self._decision(self._mcp_bulk_write_event([self.granted_abs]))
        self.assertEqual(d.get("decision", "allow"), "allow", msg=d)
        self.assertIn("sentinel", d.get("systemMessage", ""), msg=d)

    def test_a_control_single_ungranted_blocks(self) -> None:
        """Single {ungranted} candidate → block naming the path."""
        d = self._decision(self._mcp_bulk_write_event([self.ungranted_abs]))
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn(self.UNGRANTED_REL, d.get("reason", ""), msg=d)

    def test_a_control_ungranted_first_blocks_naming_offender(self) -> None:
        """{ungranted, granted} (offender FIRST) → block naming offender.

        On HEAD this passes only by ACCIDENT of the defect: the
        first-canonical break happens to select the offender when it
        comes first. It cannot carry a strict xfail (it would XPASS on
        HEAD); it is kept as an always-pass control that pins the
        post-fix contract in this order. Order-independence of the FIX
        is enforced by ``test_a_repro_fix_contract_is_order_independent``.
        """
        d = self._decision(
            self._mcp_bulk_write_event([self.ungranted_abs, self.granted_abs])
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn(self.UNGRANTED_REL, d.get("reason", ""), msg=d)

    def test_a_sk4_each_path_granted_by_own_sentinel_allows(self) -> None:
        """Anti-over-block (SK4): {grantedByS1, grantedByS2} → allow.

        Each candidate is covered by its OWN valid sentinel;
        most-restrictive-wins must not degrade into 'one sentinel must
        cover everything'. Exercised in BOTH orders.
        """
        self._write_sentinel("PLAN-202", [self.UNGRANTED_REL])
        for order in (
            [self.granted_abs, self.ungranted_abs],
            [self.ungranted_abs, self.granted_abs],
        ):
            d = self._decision(self._mcp_bulk_write_event(order))
            self.assertEqual(
                d.get("decision", "allow"),
                "allow",
                msg=f"order={order}: {d}",
            )

    # ---- repros (xfail-strict on HEAD; MUST pass after Wave-2 fix) -------

    @_XFAIL_A
    def test_a_repro_granted_first_smuggles_ungranted(self) -> None:
        """DEFECT REPRO: {granted, ungranted} → the whole event is ALLOWED
        on HEAD (the break selects the granted candidate; the ungranted
        canonical path rides along unexamined).

        Post-fix contract asserted here: the event must BLOCK and the
        reason must name the OFFENDING candidate (the ungranted path),
        not merely ``candidate_paths[0]`` (which is the granted one in
        this order).
        """
        d = self._decision(
            self._mcp_bulk_write_event([self.granted_abs, self.ungranted_abs])
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn(self.UNGRANTED_REL, d.get("reason", ""), msg=d)

    @_XFAIL_A
    def test_a_repro_fix_contract_is_order_independent(self) -> None:
        """DEFECT REPRO (both orders): the fixed gate must block the
        {granted, ungranted} event in EVERY candidate order, naming the
        offender each time — candidate ordering must never rescue or
        doom the decision.

        Fails on HEAD via the granted-first order (allowed). A Wave-2
        'fix' that merely reorders candidates cannot satisfy this test.
        """
        for order in (
            [self.granted_abs, self.ungranted_abs],
            [self.ungranted_abs, self.granted_abs],
        ):
            d = self._decision(self._mcp_bulk_write_event(order))
            self.assertEqual(
                d.get("decision"), "block", msg=f"order={order}: {d}"
            )
            self.assertIn(
                self.UNGRANTED_REL,
                d.get("reason", ""),
                msg=f"order={order}: {d}",
            )


class SentinelCacheKeyRegressionTest(TestEnvContext):
    """A×B interaction regression (always-pass): the sentinel-verify
    cache key must include ``target_rel`` so a grant decision for one
    target can never be replayed for another (PLAN-094 iter-1 P0 fix
    must survive the Wave-2 rework of the candidate loop).
    """

    def test_a_cachekey_distinct_target_rel_distinct_keys(self) -> None:
        mod = _load_hook_module()
        sentinel = self.project_dir / "approved.md"
        sentinel.write_text("Approved-By: @x deadbeef\n", encoding="utf-8")
        key_a = mod._compute_sentinel_cache_key(sentinel, ".claude/team.md")
        key_b = mod._compute_sentinel_cache_key(
            sentinel, ".claude/frontend-team.md"
        )
        self.assertIsNotNone(key_a)
        self.assertIsNotNone(key_b)
        self.assertNotEqual(key_a, key_b)
        # Same target_rel → identical key (cache still functions).
        key_a2 = mod._compute_sentinel_cache_key(sentinel, ".claude/team.md")
        self.assertEqual(key_a, key_a2)


# ===========================================================================
# Finding D — relative-path classification bypass
# ===========================================================================
class FindingDRelativePathTest(_CouncilFindingsBase):
    """Council finding D: ``_is_canonical`` resolves ``path_str`` against
    the PROCESS CWD; a relative path to a canonical file, evaluated from
    a cwd outside the repo, resolves outside ``repo_root`` and is
    classified non-canonical → allow (bypass).

    NOTE: this input makes ``_is_canonical`` return False, so the
    finding-C except branch is never reached on this path — D input is
    deliberately NOT reused to verify C.
    """

    TARGET_REL = ".claude/team.md"

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()  # no sentinel: block is the granted-free outcome
        self.elsewhere = self._tmp_root / "elsewhere"
        self.elsewhere.mkdir(exist_ok=True)

    @_XFAIL_D
    def test_d_repro_relative_canonical_path_is_gated(self) -> None:
        """DEFECT REPRO: relative ``file_path`` for a canonical file,
        hook subprocess run with ``cwd`` != CLAUDE_PROJECT_DIR → HEAD
        classifies it non-canonical and ALLOWS. Post-fix: the relative
        path is treated as canonical and (with no sentinel) BLOCKS,
        naming the target.
        """
        d = self._decision(
            {
                "hook_event_name": "PreToolUse",
                "session_id": "plan160-w1",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": self.TARGET_REL,
                    "old_string": "team",
                    "new_string": "TAMPERED",
                },
            },
            cwd=str(self.elsewhere),
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn("team.md", d.get("reason", ""), msg=d)

    def test_d_control_absolute_twin_blocks(self) -> None:
        """Twin control (always-pass): the SAME file via an ABSOLUTE
        path, same foreign cwd → classified canonical and blocked
        without a sentinel. Proves the D fix must not change absolute
        classification.
        """
        d = self._decision(
            {
                "hook_event_name": "PreToolUse",
                "session_id": "plan160-w1",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(self.project_dir / self.TARGET_REL),
                    "old_string": "team",
                    "new_string": "TAMPERED",
                },
            },
            cwd=str(self.elsewhere),
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn("CANONICAL-EDIT-BLOCKED", d.get("reason", ""), msg=d)
        self.assertIn(self.TARGET_REL, d.get("reason", ""), msg=d)


# ===========================================================================
# Finding C — dead fail-open except in decide() (property + forced branch)
# ===========================================================================
class FindingCDeadnessTest(TestEnvContext):
    """Council finding C, as re-diagnosed by the PLAN-160 W0 debate: the
    ``except (ValueError, OSError) -> allow`` at decide() L1136-1139 is
    DEAD code in same-process terms — whenever ``_is_canonical`` returned
    True, the identical resolve in decide() must also succeed (only a
    same-process TOCTOU between the two calls can reach the except).
    Hence: a deadness PROPERTY (passes on HEAD) + a forced-branch
    white-box test for the not-yet-added defense-in-depth (xfail-strict).
    """

    def _layout(self) -> None:
        (self.project_dir / ".claude").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "team.md").write_text(
            "team", encoding="utf-8"
        )
        (self.project_dir / ".claude" / "frontend-team.md").write_text(
            "front", encoding="utf-8"
        )
        hooks = self.project_dir / ".claude" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "check_probe.py").write_text("# hook", encoding="utf-8")

    def test_c_property_canonical_implies_decide_resolve_succeeds(self) -> None:
        """PROPERTY (passes on HEAD): over a varied path set — relative,
        absolute, dot-dot, symlink (inside + outside the repo),
        over-long, unicode — ``_is_canonical(p) is True`` implies the
        decide()-equivalent resolve (L1136-1139:
        ``Path(p).resolve().relative_to(repo_root.resolve())``) also
        succeeds. Proves the except is unreachable except via
        same-process TOCTOU. Anti-vacuity: at least 3 paths must
        actually classify canonical.
        """
        mod = _load_hook_module()
        self._layout()
        repo_root = self.project_dir

        # Symlink INSIDE the repo → resolves to a canonical file.
        link_inside = self._tmp_root / "team-link.md"
        # Symlink pointing OUTSIDE the repo root.
        outside_target = self._tmp_root / "outside-target.txt"
        outside_target.write_text("x", encoding="utf-8")
        link_outside = self.project_dir / "outside-link.md"
        try:
            link_inside.symlink_to(self.project_dir / ".claude" / "team.md")
            link_outside.symlink_to(outside_target)
        except OSError:  # pragma: no cover - fs without symlink support
            pass

        varied = [
            # absolute, existing canonical files
            str(self.project_dir / ".claude" / "team.md"),
            str(self.project_dir / ".claude" / "frontend-team.md"),
            str(self.project_dir / ".claude" / "hooks" / "check_probe.py"),
            # absolute with dot-dot traversal (resolve() normalizes)
            str(
                self.project_dir / ".claude" / ".." / ".claude" / "team.md"
            ),
            # unicode segment matching a canonical glob (non-existent is
            # fine — resolve(strict=False) does not require existence)
            str(
                self.project_dir / ".claude" / "skills" / "core"
                / "ünïcode-skill" / "SKILL.md"
            ),
            # symlinks
            str(link_inside),
            str(link_outside),
            # relative forms (resolve against the pytest process cwd —
            # OUTSIDE this tmp repo root, so classified non-canonical;
            # the property is implication-shaped, these exercise the
            # False side. This is exactly finding D's surface.)
            ".claude/team.md",
            "docs/notes.md",
            # outside the repo
            "/etc/passwd",
            str(self._tmp_root / "unrelated.txt"),
            # over-long single segment (> NAME_MAX): resolve may raise
            # OSError inside _is_canonical, which returns False — the
            # implication stays vacuously true, never inconsistent.
            str(self.project_dir / ".claude" / ("x" * 600 + ".md")),
            # empty-ish / odd
            ".",
        ]

        canonical_true = 0
        for p in varied:
            canon = mod._is_canonical(p, repo_root)
            if not canon:
                continue
            canonical_true += 1
            try:
                rel = str(
                    Path(p).resolve().relative_to(repo_root.resolve())
                ).replace(os.sep, "/")
            except (ValueError, OSError) as exc:  # pragma: no cover
                self.fail(
                    "deadness property violated: _is_canonical(%r) is True "
                    "but the decide()-equivalent resolve raised %r — the "
                    "decide() except branch IS reachable without TOCTOU"
                    % (p, exc)
                )
            self.assertTrue(rel, msg=p)
        self.assertGreaterEqual(
            canonical_true,
            3,
            msg=(
                "anti-vacuity guard: property never exercised the "
                "canonical-True side (fixture broken?)"
            ),
        )

    @_XFAIL_C
    def test_c_forced_branch_resolve_fault_must_block(self) -> None:
        """FORCED-BRANCH (branch-coverage of defense-in-depth, NOT a
        repro): monkeypatch the module's ``Path`` so ``.resolve()``
        raises OSError AFTER ``_is_canonical`` has confirmed the target
        canonical (confirmation simulated by patching ``_is_canonical``
        to True — its own internal resolve would otherwise fail first).
        The STILL-UNSHIPPED Wave-2 defense must turn this fault into a
        BLOCK whose reason carries ``canonical_edit_hook_fault``; HEAD
        fail-opens to allow (xfail-strict documents that).
        """
        mod = _load_hook_module()
        self._layout()
        target = str(self.project_dir / ".claude" / "team.md")

        class _ResolveFaultPath(type(Path())):
            def resolve(self, *args, **kwargs):
                raise OSError(
                    "PLAN-160 finding C forced TOCTOU: resolve fault "
                    "after canonical confirmation"
                )

        from unittest import mock

        with mock.patch.object(
            mod, "_is_canonical", lambda _p, _r: True
        ), mock.patch.object(mod, "Path", _ResolveFaultPath):
            out = mod.decide(file_path=target, repo_root=self.project_dir)
        d = json.loads(out)
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn("canonical_edit_hook_fault", d.get("reason", ""), msg=d)


# ===========================================================================
# Finding B — sentinel cache blast radius (characterization, no xfail)
# ===========================================================================
class FindingBCacheBlastRadiusTest(_CouncilFindingsBase):
    """Council finding B (revocation staleness): characterization test,
    PASSES on HEAD by design (an xfail here would be green-vacuous).
    Behavioral, not stat-introspective: because each hook invocation is
    a FRESH process, the module-scope sentinel-verify cache dies with
    the process — a Scope revocation on disk takes effect on the very
    next invocation. This pins the cache's blast radius to a single
    invocation; Wave 2 must not regress it (e.g. via a file-backed
    cache).
    """

    TARGET_REL = ".claude/team.md"

    def test_b_scope_revocation_takes_effect_next_invocation(self) -> None:
        self._make_repo_layout()
        target_abs = str(self.project_dir / self.TARGET_REL)
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "plan160-w1",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": target_abs,
                "old_string": "team",
                "new_string": "TAMPERED",
            },
        }

        # Invocation 1 — sentinel grants the target → allow via sentinel.
        self._write_sentinel("PLAN-203", [self.TARGET_REL])
        d1 = self._decision(payload)
        self.assertEqual(d1.get("decision", "allow"), "allow", msg=d1)
        self.assertIn("PLAN-203", d1.get("systemMessage", ""), msg=d1)

        # Revoke on disk: rewrite the SAME sentinel file with a Scope
        # that no longer lists the target.
        self._write_sentinel("PLAN-203", [".claude/pitfalls-catalog.yaml"])

        # Invocation 2 — a FRESH subprocess must see the revocation.
        d2 = self._decision(payload)
        self.assertEqual(d2.get("decision"), "block", msg=d2)
        self.assertIn(self.TARGET_REL, d2.get("reason", ""), msg=d2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
