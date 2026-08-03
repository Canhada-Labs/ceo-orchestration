"""PLAN-162 Wave 1 — red-first verification instruments for the round-1
debate consensus findings on ``check_canonical_edit.py`` (+ its kernel
sibling ``check_arbitration_kernel.py``).

This file is a VERIFICATION INSTRUMENT, not a fix. The target hooks are
canonical-guarded AND kernel-guarded — the fix lands by Owner-signed
ceremony, so W1's deliverable is the PROOF, not the patch. Every defect
is documented via ``xfail(strict=True)``: strict turns an unexpected pass
into a FAILURE, so a test that passes by accident before the fix breaks
the gate instead of quietly vanishing.

Methodological precedent: ``test_canonical_edit_council_findings.py``
(PLAN-160 W1, consensus S4). Same shape — a marker string in the SOURCE
of the hook-under-test drives the per-finding flag — and the fixture
helpers (``_write_sentinel`` / ``_mcp_bulk_write_event`` /
``_make_repo_layout``) are INHERITED from that file's
``_CouncilFindingsBase`` rather than re-derived.

## Feature-detect contract (W2 depends on this — do not change)

The fixed hooks will carry module-level markers. This file reads the
SOURCE of each hook-under-test and derives per-finding flags::

    FIXED_2 = "PLAN162_FIX_2" in _HOOK_SOURCE          # canonical hook only
    FIXED_CASEFOLD = marker in BOTH hook sources        # two-rail fixes

Two-rail findings (S1 case-fold, #3+#8 guard-the-guardfiles) require the
marker in BOTH ``check_canonical_edit.py`` AND
``check_arbitration_kernel.py``. A HALF fix therefore leaves the flag
False, the now-passing half XPASSes, and strict-xfail fails the gate —
which is the point: neither rail may be fixed alone.

Hooks-under-test are env-overridable so W2 can point the SAME tests at a
staged copy:

    PLAN162_HOOK_PATH    -> check_canonical_edit.py    (default: canonical)
    PLAN162_KERNEL_PATH  -> check_arbitration_kernel.py

NOTE for W2 when choosing marker names: flag detection is a SUBSTRING
test, so a future ``PLAN162_FIX_10`` would also satisfy
``"PLAN162_FIX_1" in source``. The consensus folds #1+#10 under the
single marker ``PLAN162_FIX_1`` precisely so that ambiguity never
arises — do not introduce ``PLAN162_FIX_1<digit>``.

## Instrument map (consensus disposition -> class)

* **S1 case-insensitive bypass, P0** (``S1CaseFoldBypassTest``):
  ``fnmatch.fnmatchcase`` in ``_match_segments`` makes
  ``.claude/settings.JSON`` and ``.claude/hooks/_lib/audit_emit.PY``
  classify NON-canonical and NON-kernel while APFS (this repo's
  platform) resolves them to the very files both rails exist to
  protect. Probed on HEAD before writing: both variants False on both
  rails; the repo filesystem is case-insensitive.
* **#1 + #10 cache partition** (``Finding1And10CachePartitionTest``):
  IN-PROCESS by construction (consensus S5 — a subprocess repro dies with
  the module-scope cache and XPASSes by accident, per
  ``FindingBCacheBlastRadiusTest``). Two properties: signature
  verification must run once per SENTINEL (not per sentinel x target),
  and the signing-material bytes (``.asc`` / allowlist / registry) must
  participate in the cache key. The call-COUNT instrument is the
  load-bearing one for #1 and is fully deterministic — no clock, no
  sleep.
* **#1 wall-clock deadline** (``Finding1WallDeadlineTest``): the other
  half of the same patch (C2 + C3), under the S8 addendum. Carries a
  static registration-drift check and a deadline repro driven by an
  INJECTED clock seam — never a real sleep. The seam name is a contract
  ON the fix; see that class's docstring.
* **#2 symlink depth-independence** (``Finding2SymlinkDepthTest``):
  ``_find_sentinels`` checks ``p``, ``p.parent``, ``p.parent.parent`` —
  the ``PLAN-*`` segment above them is unchecked, so a symlinked
  ``PLAN-*`` directory smuggles a foreign sentinel in. Positive control:
  the ``p.parent`` symlink the guard DOES catch.
* **#3 + #8 guard-the-guardfiles**
  (``Finding3And8GuardTheGuardfilesTest``): the sentinel signer registry
  and the policy drift manifest are unguarded on BOTH rails.
* **#4 scope containment** (``Finding4ScopeContainmentTest``): a BEGIN
  marker must never silently downgrade to the Tier-2 whole-file parser;
  oversize must reject fail-closed; the END marker must terminate a
  Tier-2 scope block.
* **#5a/#5b failure posture** (``Finding5FailurePostureTest``): 5a
  (``read_event`` raises -> allow) is ACCEPTed and gets a PIN that passes
  today; 5b (``event.parse_error`` -> allow) is the drift and gets the
  red-first repro. Neither direction was fixed by any test before this
  file (``grep parse_error`` over the hook's 8 test files: zero hits).
* **#7 file:// URI** (``Finding7FileUriTest``).
* **#9 blocked_tool forensics** (``Finding9BlockedToolForensicTest``):
  one behavioral repro through the audit log, one always-pass injection
  PIN, and a SOURCE-level fence covering all four sites at once (two of
  the four — the session-roots deny and the registry-tamper emit — are
  not economically reachable behaviorally from this surface).
* **S2 sentinel trust anchor** (``S2SentinelUnderEnvOverrideTest``):
  under ``CEO_SENTINEL_UNLOCK`` the GPG rail is skipped entirely, so an
  ``approved.md`` the agent writes mid-session GRANTS. Requires ``git``.
* **S6 interaction pass** (``InteractionPassTest``): the #2 fix changes
  which candidates ``_find_sentinels`` returns and the #7 fix changes
  what ``_canonical_rel`` yields for ``uri`` candidates, which lands in
  the #9 forensic field on the SAME event.

## Not covered here (by consensus)

#6 and #11 are DOC-GAP, #12 is ACCEPT with a named reopen trigger — no
test is written for a disposition that ships no behavior change.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

import pytest

# Post-canonical-promotion layout: parents[0]=tests/ [1]=hooks/.
# The root conftest already seeds sys.path; the explicit inserts keep
# `python3 -m unittest` discovery and the sibling-module import working.
_TESTS_DIR = Path(__file__).resolve().parents[0]
_HOOKS_DIR = Path(__file__).resolve().parents[1]
for _p in (str(_HOOKS_DIR), str(_TESTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402

# Consensus S4: reuse the PLAN-160 fixture helpers instead of re-deriving
# them. Only the pure fixture surface is inherited (`_make_repo_layout`,
# `_write_sentinel`, `_mcp_bulk_write_event`); the subprocess runner is
# NOT reused because it force-sets CEO_SENTINEL_UNLOCK by default, and
# most PLAN-162 instruments must exercise the GPG rail (or, for S2, own
# the unlock env explicitly).
from test_canonical_edit_council_findings import (  # noqa: E402
    _CouncilFindingsBase,
)

# ---------------------------------------------------------------------------
# Hooks under test + per-finding feature-detect flags.
# ---------------------------------------------------------------------------
_HOOK_PATH = Path(
    os.environ.get("PLAN162_HOOK_PATH")
    or str(_HOOKS_DIR / "check_canonical_edit.py")
).resolve()
_KERNEL_PATH = Path(
    os.environ.get("PLAN162_KERNEL_PATH")
    or str(_HOOKS_DIR / "check_arbitration_kernel.py")
).resolve()

_HOOK_SOURCE = _HOOK_PATH.read_text(encoding="utf-8")
_KERNEL_SOURCE = _KERNEL_PATH.read_text(encoding="utf-8")

# The LIVE registration surface (never the per-test tmp project): the
# wall-clock budget constant is checked for drift against the timeout
# registered here (consensus C3). Deliberately NOT redirected by
# PLAN162_HOOK_PATH — a staged hook copy is still governed by the live
# settings.json registration.
_SETTINGS_PATH = _HOOKS_DIR.parents[1] / ".claude" / "settings.json"


def _in_hook(marker: str) -> bool:
    return marker in _HOOK_SOURCE


def _in_both_rails(marker: str) -> bool:
    """Two-rail marker: a half fix must NOT flip the flag (see docstring)."""
    return marker in _HOOK_SOURCE and marker in _KERNEL_SOURCE


FIXED_CASEFOLD = _in_both_rails("PLAN162_FIX_CASEFOLD")
FIXED_1 = _in_hook("PLAN162_FIX_1")
FIXED_2 = _in_hook("PLAN162_FIX_2")
FIXED_3 = _in_both_rails("PLAN162_FIX_3")
FIXED_4 = _in_hook("PLAN162_FIX_4")
FIXED_5B = _in_hook("PLAN162_FIX_5B")
FIXED_7 = _in_hook("PLAN162_FIX_7")
FIXED_9 = _in_hook("PLAN162_FIX_9")
FIXED_S2 = _in_hook("PLAN162_FIX_S2")


def _xfail(fixed: bool, label: str):
    return pytest.mark.xfail(
        condition=not fixed,
        reason=(
            "PLAN-162 {0}: defect present on HEAD; flips after the W2 "
            "ceremony fix".format(label)
        ),
        strict=True,
    )


_XFAIL_CASEFOLD = _xfail(FIXED_CASEFOLD, "S1 (case-fold, P0)")
_XFAIL_1 = _xfail(FIXED_1, "#1+#10 (cache partition)")
_XFAIL_2 = _xfail(FIXED_2, "#2 (symlink depth-independence)")
_XFAIL_3 = _xfail(FIXED_3, "#3+#8 (guard-the-guardfiles)")
_XFAIL_4 = _xfail(FIXED_4, "#4 (scope containment)")
_XFAIL_5B = _xfail(FIXED_5B, "#5b (parse_error fail-closed)")
_XFAIL_7 = _xfail(FIXED_7, "#7 (file:// URI)")
_XFAIL_9 = _xfail(FIXED_9, "#9 (blocked_tool forensics)")
_XFAIL_S2 = _xfail(FIXED_S2, "S2 (sentinel under env_override)")
_XFAIL_7X9 = _xfail(FIXED_7 and FIXED_9, "S6 interaction #7 x #9")


# ---------------------------------------------------------------------------
# In-process (white-box) loaders. UNIQUE module names so the canonical
# `check_canonical_edit` import used by sibling test files is never
# clobbered (xdist-safe: per-process cache; every monkeypatch below uses a
# `mock.patch.object` context manager, which restores on exit).
# ---------------------------------------------------------------------------
_MODULE_CACHE: Dict[str, object] = {}


def _load_module(alias: str, path: Path):
    key = alias + "@" + str(path)
    mod = _MODULE_CACHE.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(alias, str(path))
        if spec is None or spec.loader is None:  # pragma: no cover
            raise RuntimeError("PLAN-162: cannot load {0}".format(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULE_CACHE[key] = mod
    return mod


def _load_hook():
    return _load_module("plan162_hook_under_test", _HOOK_PATH)


def _load_kernel():
    return _load_module("plan162_kernel_under_test", _KERNEL_PATH)


# ---------------------------------------------------------------------------
# Shared fixtures / harness
# ---------------------------------------------------------------------------
_TEAM_REL = ".claude/team.md"
_FRONT_REL = ".claude/frontend-team.md"
_APPROVED_BY = "Approved-By: @Canhada-Labs deadbeef\n"


class _GpgStub:
    """Stand-in for ``_lib.gpg_verify`` with a call counter.

    Lets the scope-parser and cache instruments exercise the REAL
    (non-``env_override``) code path without a live gpg-agent, and makes
    the number of signature verifications observable — which is exactly
    what finding #1 is about.
    """

    def __init__(self, ok: bool = True, fpr: str = "FPR0") -> None:
        self.ok = ok
        self.fpr = fpr
        self.calls = 0

    def verify_detached(self, *args, **kwargs):
        self.calls += 1
        return (self.ok, self.fpr, "plan162-stub")


class _SignerRegistryStub:
    """Stand-in for ``_lib.sentinel_signers`` (the ADR-121 YAML rail)."""

    def __init__(self, valid: bool = True) -> None:
        self.valid = valid

    def load_registry(self, path):
        return {"plan162": "stub"}

    def is_valid_signer(self, fpr, registry=None):
        return (self.valid, "plan162-stub")


class _Plan162Base(_CouncilFindingsBase):
    """Subprocess harness with EXPLICIT env control.

    Deliberately does NOT reuse ``_CouncilFindingsBase._invoke``: that
    runner force-sets ``CEO_SENTINEL_UNLOCK`` so PLAINTEXT sentinels are
    honored, which would (a) hide the GPG rail these instruments care
    about and (b) collide with S2, whose whole subject is the unlock
    path. The fixture builders (``_make_repo_layout`` / ``_write_sentinel``
    / ``_mcp_bulk_write_event``) ARE inherited.

    ``os.environ`` is already isolated by ``TestEnvContext.setUp`` (tmp
    HOME / CLAUDE_PROJECT_DIR / CEO_AUDIT_LOG_*), so the child inherits
    the isolation; ``env_extra`` only ADDS on top.
    """

    def _run(
        self,
        stdin_text: str,
        hook: Optional[Path] = None,
        env_extra: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ):
        env = {**os.environ}
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, str(hook or _HOOK_PATH)],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            cwd=cwd,
        )

    def _decision_raw(self, stdin_text: str, **kwargs) -> dict:
        proc = self._run(stdin_text, **kwargs)
        self.assertEqual(
            proc.returncode,
            0,
            msg="stdout={0!r} stderr={1!r}".format(proc.stdout, proc.stderr),
        )
        out = proc.stdout.strip()
        self.assertTrue(
            out, msg="ZERO-EMIT: hook produced no decision line"
        )
        return json.loads(out.splitlines()[-1])

    def _decision(self, payload: dict, **kwargs) -> dict:
        return self._decision_raw(json.dumps(payload), **kwargs)

    @staticmethod
    def _edit_event(file_path: str, tool_name: str = "Edit") -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "session_id": "plan162-w1",
            "tool_name": tool_name,
            "tool_input": {
                "file_path": file_path,
                "old_string": "x",
                "new_string": "TAMPERED",
            },
        }

    @staticmethod
    def _mcp_event(tool_input: dict, tool_name: str = "mcp__future__bulk_write") -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "session_id": "plan162-w1",
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

    def _veto_events(self) -> List[dict]:
        """All ``veto_triggered`` events in this test's isolated audit log."""
        events: List[dict] = []
        for line in self.read_audit_log().splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict) and ev.get("action") == "veto_triggered":
                events.append(ev)
        return events


class _SentinelParserBase(TestEnvContext):
    """In-process base for the sentinel-parser / cache instruments.

    Every test here drives ``_sentinel_grants_path`` directly with the GPG
    rail STUBBED — not with ``CEO_SENTINEL_UNLOCK``. That matters twice
    over: it is the production (signed) code path, and it keeps these
    instruments independent of the S2 fix, which is scoped to
    ``env_override`` and would otherwise invalidate every fixture here
    (consensus S6, interaction pass).
    """

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_hook()
        self.mod._SENTINEL_VERIFY_CACHE.clear()
        (self.project_dir / ".claude").mkdir(parents=True, exist_ok=True)
        (self.project_dir / _TEAM_REL).write_text("team", encoding="utf-8")
        self.gpg = _GpgStub()
        self._no_registry = self._tmp_root / "absent-registry.yaml"

    def tearDown(self) -> None:
        self.mod._SENTINEL_VERIFY_CACHE.clear()
        super().tearDown()

    def _gpg_rail(self, registry_path: Optional[Path] = None):
        """Context manager patching the signature rail onto the stub."""
        return mock.patch.multiple(
            self.mod,
            _gpg_verify=self.gpg,
            _SENTINEL_SIGNERS_REGISTRY_YAML=(
                registry_path if registry_path is not None
                else self._no_registry
            ),
        )

    def _sentinel(self, plan_id: str, body: str) -> Path:
        d = (
            self.project_dir / ".claude" / "plans" / plan_id
            / "architect" / "round-1"
        )
        d.mkdir(parents=True, exist_ok=True)
        target = d / "approved.md"
        target.write_text(body, encoding="utf-8")
        (d / "approved.md.asc").write_text("PLAN162-SIG", encoding="utf-8")
        return target


# ===========================================================================
# S1 — case-insensitive filesystem bypass (P0, both rails)
# ===========================================================================
class S1CaseFoldBypassTest(_Plan162Base):
    """Consensus S1 (VETO-flagged, P0). ``_match_segments`` matches guard
    globs with ``fnmatch.fnmatchcase`` in BOTH hooks. On a case-insensitive
    filesystem — APFS, the default on this repo's platform —
    ``.claude/settings.JSON`` IS ``.claude/settings.json``, yet it
    classifies non-canonical AND non-kernel. That reaches the kernel
    HARD-DENY surface (settings.json, audit_emit.py, the signer
    allowlist), which the entire threat model assumes unreachable.

    The classification repro is filesystem-INDEPENDENT (it asserts on the
    predicates, which never consult the filesystem for case), so it is
    honest on a case-sensitive CI runner too; the separate
    ``..._filesystem_collides`` test records the EXPLOITABILITY evidence
    and skips where the filesystem is case-sensitive.

    Fix direction (consensus): case-fold normalization on both rails —
    over-classifying is the safe direction.
    """

    # (exact-case path, case-variant path) — both currently guarded on
    # BOTH rails in their exact case.
    #
    # The third row varies the FIRST SEGMENT on purpose. ``_is_canonical``
    # bails out in O(1) unless the first segment is in
    # ``_CANONICAL_PREFIXES`` (an exact-case frozenset), so a fix that
    # case-folds only the glob matcher leaves ``.CLAUDE/...`` classified
    # non-canonical — the guard would LOOK fixed while staying inert. That
    # is the dead-gate class this file has already been bitten by twice
    # (the ``.codex`` and ``.grok`` prefix omissions), so it is fenced
    # here rather than left for a later probe.
    BOTH_RAIL_VARIANTS = (
        (".claude/settings.json", ".claude/settings.JSON"),
        (".claude/hooks/_lib/audit_emit.py", ".claude/hooks/_lib/audit_emit.PY"),
        (".claude/settings.json", ".CLAUDE/settings.json"),
    )
    # Kernel-only today (canonical guard never covered the .txt).
    KERNEL_VARIANT = (".claude/sentinel-signers.txt", ".claude/sentinel-signers.TXT")

    def setUp(self) -> None:
        super().setUp()
        self.hook = _load_hook()
        self.kernel = _load_kernel()
        for exact, _variant in self.BOTH_RAIL_VARIANTS + (self.KERNEL_VARIANT,):
            p = self.project_dir / exact
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")

    def _abs(self, rel: str) -> str:
        return str(self.project_dir / rel)

    # ---- controls (always pass — fixture validity + anti-over-block) -----

    def test_s1_control_exact_case_is_guarded_on_both_rails(self) -> None:
        """Anti-vacuity: the exact-case twins ARE guarded today. Without
        this, an S1 'repro' could pass for the wrong reason (e.g. a broken
        repo_root making everything classify canonical)."""
        for exact, _v in self.BOTH_RAIL_VARIANTS:
            self.assertTrue(
                self.hook._is_canonical(self._abs(exact), self.project_dir),
                msg="canonical rail lost {0}".format(exact),
            )
            self.assertTrue(
                self.kernel._is_kernel_path(self._abs(exact), self.project_dir),
                msg="kernel rail lost {0}".format(exact),
            )
        self.assertTrue(
            self.kernel._is_kernel_path(
                self._abs(self.KERNEL_VARIANT[0]), self.project_dir
            )
        )

    def test_s1_control_unrelated_uppercase_stays_unguarded(self) -> None:
        """Anti-OVER-block fence: case-folding must not turn arbitrary
        paths canonical. A fix that simply lowercases everything into a
        match would pass the repro and fail here."""
        for rel in (".claude/NOTES.MD", "docs/README.MD", "src/Main.PY"):
            self.assertFalse(
                self.hook._is_canonical(self._abs(rel), self.project_dir),
                msg="over-classified {0} as canonical".format(rel),
            )
            self.assertFalse(
                self.kernel._is_kernel_path(self._abs(rel), self.project_dir),
                msg="over-classified {0} as kernel".format(rel),
            )

    def test_s1_evidence_filesystem_collides_case_variants(self) -> None:
        """EXPLOITABILITY evidence (skips on a case-sensitive filesystem):
        writing through the case variant overwrites the guarded file."""
        probe = self.project_dir / "CaseProbe.txt"
        probe.write_text("original", encoding="utf-8")
        twin = self.project_dir / "caseprobe.TXT"
        if not twin.exists():
            self.skipTest("filesystem is case-sensitive; S1 not exploitable here")
        twin.write_text("overwritten", encoding="utf-8")
        self.assertEqual(probe.read_text(encoding="utf-8"), "overwritten")

    # ---- repros (xfail-strict on HEAD) ----------------------------------

    @_XFAIL_CASEFOLD
    def test_s1_repro_case_variants_classify_guarded_on_both_rails(self) -> None:
        """DEFECT REPRO (filesystem-independent): each case variant of a
        guarded path must classify canonical AND kernel. HEAD returns
        False for every one of them — the variant reaches a kernel
        HARD-DENY file through a gate that never looks at it."""
        for _exact, variant in self.BOTH_RAIL_VARIANTS:
            self.assertTrue(
                self.hook._is_canonical(self._abs(variant), self.project_dir),
                msg="canonical rail: {0} classified non-canonical".format(variant),
            )
            self.assertTrue(
                self.kernel._is_kernel_path(self._abs(variant), self.project_dir),
                msg="kernel rail: {0} classified non-kernel".format(variant),
            )
        self.assertTrue(
            self.kernel._is_kernel_path(
                self._abs(self.KERNEL_VARIANT[1]), self.project_dir
            ),
            msg="kernel rail: {0} classified non-kernel".format(
                self.KERNEL_VARIANT[1]
            ),
        )

    @_XFAIL_CASEFOLD
    def test_s1_repro_end_to_end_canonical_hook_blocks_case_variant(self) -> None:
        """DEFECT REPRO end-to-end: an unsigned Edit of
        ``.claude/settings.JSON`` (no sentinel anywhere) must BLOCK. HEAD
        allows it."""
        d = self._decision(
            self._edit_event(self._abs(".claude/settings.JSON"))
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn("CANONICAL-EDIT-BLOCKED", d.get("reason", ""), msg=d)

    @_XFAIL_CASEFOLD
    def test_s1_repro_end_to_end_kernel_hook_blocks_case_variant(self) -> None:
        """DEFECT REPRO end-to-end on the SECOND rail: the kernel hook has
        no sentinel escape, so ``.claude/settings.JSON`` must BLOCK absent
        CEO_KERNEL_OVERRIDE (stripped by TestEnvContext). HEAD allows."""
        d = self._decision(
            self._edit_event(self._abs(".claude/settings.JSON")),
            hook=_KERNEL_PATH,
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn("ARBITRATION-KERNEL-BLOCKED", d.get("reason", ""), msg=d)


# ===========================================================================
# #1 + #10 — sentinel-verify cache partition (IN-PROCESS by construction)
# ===========================================================================
class Finding1And10CachePartitionTest(_SentinelParserBase):
    """Consensus C1 + S5. ``_compute_sentinel_cache_key`` folds
    ``target_rel`` into the key, but ``verify_detached`` never receives a
    target — signature validity is target-INDEPENDENT. So the same
    sentinel is cryptographically re-verified once per distinct target:
    O(candidates x sentinels) subprocesses (measured in the debate: 320
    verifications / 4.16 s for a 20-path ceremony pack, against a 5 s
    hook budget).

    The agreed fix partitions the cache in two: a target-free SIGNATURE
    rail keyed on the signing material, and a cheap target-keyed GRANT
    rail. Both properties below follow from that partition, and #10 is the
    reason the signature key must cover the ``.asc`` / allowlist /
    registry BYTES rather than only ``approved.md``.

    IN-PROCESS is mandatory (S5): each real hook invocation is a fresh
    process, so a subprocess repro would find an empty cache and XPASS.
    """

    def _nongranting_sentinels(self, count: int) -> List[Path]:
        return [
            self._sentinel(
                "PLAN-5{0:02d}".format(i),
                _APPROVED_BY + "Scope:\n  - .claude/unrelated-{0}.md\n".format(i),
            )
            for i in range(count)
        ]

    # ---- controls --------------------------------------------------------

    def test_1_control_grant_decisions_stay_target_specific(self) -> None:
        """Always-pass regression fence (PLAN-094 iter-1 P0): partitioning
        the cache must not let a grant for one target be replayed for
        another. Exercised twice per target so the second call goes
        through the cache-HIT path."""
        s = self._sentinel("PLAN-590", _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n")
        with self._gpg_rail():
            for _ in range(2):
                self.assertTrue(
                    self.mod._sentinel_grants_path(s, _TEAM_REL)
                )
                self.assertFalse(
                    self.mod._sentinel_grants_path(s, _FRONT_REL)
                )

    # ---- repros ----------------------------------------------------------

    @_XFAIL_1
    def test_1_repro_signature_verify_runs_once_per_sentinel(self) -> None:
        """DEFECT REPRO: with M sentinels and N distinct targets, the
        number of ``verify_detached`` calls must be M — signature validity
        does not depend on the target. HEAD performs M*N.

        The loop mirrors ``_candidate_is_granted``'s iteration (every
        sentinel consulted for every candidate); the sentinels grant
        nothing, which is precisely the worst case a ceremony pack hits
        before reaching the one sentinel that does grant.
        """
        sentinels = self._nongranting_sentinels(4)
        targets = [".claude/adr/ADR-{0:03d}-x.md".format(i) for i in range(5)]
        with self._gpg_rail():
            for target in targets:
                for s in sentinels:
                    self.mod._sentinel_grants_path(s, target)
        self.assertGreater(
            self.gpg.calls, 0, msg="anti-vacuity: signature rail never ran"
        )
        self.assertEqual(
            self.gpg.calls,
            len(sentinels),
            msg=(
                "signature verification amplified by target count: "
                "{0} calls for {1} sentinels x {2} targets".format(
                    self.gpg.calls, len(sentinels), len(targets)
                )
            ),
        )

    @_XFAIL_1
    def test_10_repro_asc_bytes_change_invalidates_cached_grant(self) -> None:
        """DEFECT REPRO (#10, in-process reuse): after a grant is cached,
        replacing the detached-signature BYTES must force re-verification.
        HEAD keys only on ``approved.md``'s bytes, so the tampered ``.asc``
        keeps riding the cached ``True``."""
        s = self._sentinel("PLAN-601", _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n")
        with self._gpg_rail():
            self.assertTrue(self.mod._sentinel_grants_path(s, _TEAM_REL))
            s.with_name(s.name + ".asc").write_text(
                "PLAN162-TAMPERED", encoding="utf-8"
            )
            self.gpg.ok = False
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="stale grant survived a .asc byte change",
            )

    @_XFAIL_1
    def test_10_repro_allowlist_bytes_change_invalidates_cached_grant(self) -> None:
        """DEFECT REPRO (#10): the signer ALLOWLIST is an input to the
        verification decision, so rotating/revoking in
        ``sentinel-signers.txt`` must invalidate the cached grant."""
        allowlist = self.project_dir / ".claude" / "sentinel-signers.txt"
        allowlist.parent.mkdir(parents=True, exist_ok=True)
        allowlist.write_text("FPR0\n", encoding="utf-8")
        s = self._sentinel("PLAN-602", _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n")
        with self._gpg_rail(), mock.patch.object(
            self.mod, "_SENTINEL_SIGNERS_FILE", allowlist
        ):
            self.assertTrue(self.mod._sentinel_grants_path(s, _TEAM_REL))
            allowlist.write_text("# revoked\n", encoding="utf-8")
            self.gpg.ok = False
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="stale grant survived a signer-allowlist byte change",
            )

    @_XFAIL_1
    def test_10_repro_registry_bytes_change_invalidates_cached_grant(self) -> None:
        """DEFECT REPRO (#10): the ADR-121 YAML signer registry is the
        second signer rail; a revocation landing there must invalidate the
        cached grant too."""
        registry = self.project_dir / ".claude" / "security" / "signers.yaml"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text("signers:\n  - FPR0\n", encoding="utf-8")
        signers = _SignerRegistryStub(valid=True)
        s = self._sentinel("PLAN-603", _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n")
        with self._gpg_rail(registry_path=registry), mock.patch.object(
            self.mod, "_sentinel_signers", signers
        ):
            self.assertTrue(self.mod._sentinel_grants_path(s, _TEAM_REL))
            registry.write_text("signers: []\n", encoding="utf-8")
            signers.valid = False
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="stale grant survived a signer-registry byte change",
            )


class Finding1WallDeadlineTest(_SentinelParserBase):
    """Consensus C2 + C3 (the second half of the #1 patch), under the S8
    addendum: the deadline needs an INJECTABLE CLOCK.

    C2 removed the sentinel cap from the design — ``_find_sentinels``
    returns sorted, so the highest-numbered (freshly-signed) pack is
    exactly the sentinel a cap would drop, self-DoS with the Owner's
    signature in hand. What replaces it is a global wall-clock deadline
    per INVOCATION, checked at the top of the sentinel loops, that fails
    CLOSED (``canonical_edit_hook_fault``) — never "allow because we did
    not finish deciding", never "stop checking sentinels".

    C3 keeps the budget as a MODULE CONSTANT (``_HOOK_WALL_BUDGET_S``)
    rather than reading settings.json at runtime: the budget lives in the
    file this hook guards, and parsing JSON on the hot path would worsen
    the very path being optimized. The registration-drift check is a
    static test instead — the shape ``verify-counts.sh`` already uses.

    ## Seam requirement (S8) — this is a CONTRACT on the fix, not a hint

    The tests below never sleep. Real sleeps against a multi-second budget
    are flaky under runner load, a class already documented in this repo.
    The fix MUST therefore expose the clock as a module-level seam named
    ``_now`` (default ``time.monotonic``) so a test can drive the deadline
    deterministically. ``test_1_repro_expired_deadline_fails_closed_via_
    injected_clock`` asserts that seam by name and fails with an explicit
    message if it is absent — the requirement travels with the proof
    instead of being discovered at implementation time.

    Ordering is not negotiable (C3): the deadline and the cache partition
    ship in the SAME patch under the SAME ``PLAN162_FIX_1`` marker. A
    deadline without the partition fires on the 4.16 s the debate measured
    and denies the ceremony itself; landing the marker with only half the
    patch turns the other half's tests red, which is the intended fence.
    """

    def setUp(self) -> None:
        super().setUp()
        (self.project_dir / _FRONT_REL).write_text("front", encoding="utf-8")

    # ---- helpers ---------------------------------------------------------

    def _registered_timeouts(self) -> List[float]:
        """Timeouts registered for this hook in the LIVE settings.json."""
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        found: List[float] = []
        for entries in (data.get("hooks") or {}).values():
            for entry in entries or []:
                for h in entry.get("hooks") or []:
                    if "check_canonical_edit" in (h.get("command") or ""):
                        timeout = h.get("timeout")
                        if isinstance(timeout, (int, float)):
                            found.append(float(timeout))
        return found

    def _granted_multi_event(self) -> dict:
        """A multi-candidate event whose every canonical path IS granted —
        so the normal-clock outcome is ALLOW and any block below can only
        come from the deadline."""
        self._sentinel(
            "PLAN-610",
            _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n  - " + _FRONT_REL + "\n",
        )
        return {
            "hook_event_name": "PreToolUse",
            "session_id": "plan162-w1",
            "tool_name": "mcp__future__bulk_write",
            "tool_input": {
                "path": [
                    str(self.project_dir / _TEAM_REL),
                    str(self.project_dir / _FRONT_REL),
                ],
                "content": "x",
            },
        }

    def _main_decision(self, payload: dict, clock=None) -> dict:
        """Drive ``main()`` IN-PROCESS with the signature rail stubbed and,
        optionally, the clock seam replaced. In-process because the seam is
        a monkeypatch — it cannot be staged on disk."""
        stdout = io.StringIO()
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project_dir)}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, env, clear=True))
            stack.enter_context(
                mock.patch.object(self.mod, "_gpg_verify", self.gpg)
            )
            stack.enter_context(
                mock.patch.object(
                    self.mod,
                    "_SENTINEL_SIGNERS_REGISTRY_YAML",
                    self._no_registry,
                )
            )
            if clock is not None:
                stack.enter_context(mock.patch.object(self.mod, "_now", clock))
            stack.enter_context(
                mock.patch("sys.stdin", io.StringIO(json.dumps(payload)))
            )
            stack.enter_context(contextlib.redirect_stdout(stdout))
            rc = self.mod.main()

        self.assertEqual(rc, 0)
        out = stdout.getvalue().strip()
        self.assertTrue(out, msg="ZERO-EMIT: main() produced no decision")
        return json.loads(out.splitlines()[-1])

    # ---- controls --------------------------------------------------------

    def test_1_control_hook_registration_is_discoverable(self) -> None:
        """Anti-vacuity for the drift check (always-pass). A settings.json
        walk that matches NOTHING would make the drift assertion below
        pass while comparing against an empty set — the vacuous-gate class
        this repo hit in S287 with verify-counts. Assert the registration
        is actually found before anything is compared to it.

        This reads the LIVE settings.json rather than the per-test tmp
        project. That is parallel-safe: the file is canonical- AND
        kernel-guarded, so no test in the suite writes it — the read has
        no racing writer.

        NAMING (deliberate): the root ``conftest.py`` auto-marks any test
        whose NODE ID matches ``budget|timeout|perf|latency|...`` as
        ``serial``. This test and its sibling below are pure static reads
        with no timing assertion whatsoever, so the obvious names
        (``..._registered_timeout...``, ``..._wall_budget...``) would
        misroute them into the serial lane. W2 should keep that in mind
        when naming further deadline tests."""
        timeouts = self._registered_timeouts()
        self.assertEqual(
            len(timeouts),
            1,
            msg="expected exactly one check_canonical_edit registration in "
                "{0}, found {1}".format(_SETTINGS_PATH, timeouts),
        )
        self.assertGreater(timeouts[0], 0)

    def test_1_control_normal_clock_allows_the_granted_event(self) -> None:
        """Anti-vacuity for the deadline repro (always-pass, before and
        after W2): the SAME event under the REAL clock is allowed via the
        sentinel. So the block asserted below can only be the deadline —
        not a broken fixture, and not the sentinel gate."""
        d = self._main_decision(self._granted_multi_event())
        self.assertNotEqual(d.get("decision"), "block", msg=d)
        self.assertIn("PLAN-610", d.get("systemMessage", ""), msg=d)

    # ---- repros ----------------------------------------------------------

    @_XFAIL_1
    def test_1_repro_wall_deadline_constant_has_slack_under_registration(self) -> None:
        """DEFECT REPRO (C3, static drift check — no clock involved): the
        module must expose ``_HOOK_WALL_BUDGET_S``, and it must sit
        strictly UNDER the timeout registered in settings.json, with room
        left to emit the fail-closed decision after the deadline fires. A
        budget at or above the registered timeout is a deadline the
        harness kills before it can decide anything."""
        budget = getattr(self.mod, "_HOOK_WALL_BUDGET_S", None)
        self.assertIsNotNone(
            budget,
            msg="the fix must expose the wall-clock budget as a module "
                "constant _HOOK_WALL_BUDGET_S (C3: never read from "
                "settings.json at runtime — the hook guards that file, and "
                "parsing it on the hot path worsens the path being fixed)",
        )
        registered = self._registered_timeouts()[0]
        self.assertGreater(float(budget), 0.0)
        self.assertLess(
            float(budget),
            registered,
            msg="_HOOK_WALL_BUDGET_S={0} leaves no slack under the "
                "registered timeout {1}s".format(budget, registered),
        )

    @pytest.mark.skip(
        reason="PLAN-162: deadline posture is an UNRESOLVED contract conflict "
               "(consensus C2 + this file's F-01-07 fail-closed precedent vs "
               "AGENTS.md §1 / CLAUDE.md §4 'timeout -> breadcrumb + allow'). "
               "Pair-rail R4 P1. Skipped rather than xfailed: an xfail(strict) "
               "would stay green under EITHER implementation and hide the "
               "decision. W2 must land the ADR that settles it, then re-enable "
               "this test on the ratified side."
    )
    def test_1_repro_expired_deadline_fails_closed_via_injected_clock(self) -> None:
        """DEFECT REPRO (C2, S8): with the injected clock already past the
        budget, a multi-candidate event whose every path IS granted must
        still fail CLOSED — ``canonical_edit_hook_fault``. Two things are
        asserted at once, and both are the point of C2:

        * the outcome is a BLOCK, never "allow because we ran out of time";
        * the seam exists and was consulted, so no test in this pack ever
          needs a real multi-second sleep.

        The fake clock returns t0 on its first reading (the deadline
        baseline) and t0 + budget + 10 on every reading after, which is
        robust to how many times the fix samples the clock."""
        self.assertTrue(
            hasattr(self.mod, "_now"),
            msg="the fix must expose the clock as a module-level seam "
                "`_now` (default time.monotonic) so the deadline is "
                "testable without a real sleep — S8 addendum to the "
                "round-1 consensus; a sleep-based test against a "
                "multi-second budget is a known flake class in this repo",
        )
        budget = float(getattr(self.mod, "_HOOK_WALL_BUDGET_S", 4.0))

        class _ExpiredClock(object):
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self):
                self.calls += 1
                return 0.0 if self.calls == 1 else budget + 10.0

        clock = _ExpiredClock()
        d = self._main_decision(self._granted_multi_event(), clock=clock)
        self.assertGreaterEqual(
            clock.calls, 2, msg="anti-vacuity: the clock seam was not consulted"
        )
        self.assertEqual(
            d.get("decision"),
            "block",
            msg="an expired wall-clock deadline did not fail CLOSED: {0}".format(d),
        )
        self.assertIn("canonical_edit_hook_fault", d.get("reason", ""), msg=d)

    # ---------------------------------------------------------------
    # CONTRACT CONFLICT — do not silently pick a side (pair-rail R4 P1)
    # ---------------------------------------------------------------
    # The assertion above encodes deadline-expiry as fail-CLOSED. That is
    # the consensus C2 decision AND matches this file's own established
    # F-01-07 behaviour (`canonical_edit_hook_fault` blocks in three
    # places today). But it CONTRADICTS the general rule as literally
    # written in AGENTS.md §1 / CLAUDE.md §4: "Hooks never block the
    # session on a missing file, import failure, or TIMEOUT — breadcrumb
    # + {} allow".
    #
    # Both postures have a real attack, and naming them is the point:
    #   fail-OPEN on deadline  -> the S2 planted-sentinel vector inflates
    #                             the scan until the guard waves canonical
    #                             edits through (finding #1's whole thesis);
    #   fail-CLOSED on deadline -> the same vector locks the operator out
    #                             of canonical edits (the C3 self-DoS class).
    # What makes fail-closed tenable is (a) the C1 cache partition, which
    # removes the amplification that puts either in reach, and (b) the
    # existing recovery route (CEO_SENTINEL_UNLOCK + _ACK,
    # CEO_KERNEL_OVERRIDE) — a fail-closed gate without a recovery route
    # is a brick, and this one has one.
    #
    # The CEO does NOT get to settle a documented contract conflict inside
    # a test. W2 must land an ADR that either (i) carves out "a security
    # matcher that cannot establish authorization for a CONFIRMED-canonical
    # path fails closed" as an explicit exception to the infrastructure
    # rule, or (ii) reverses this assertion to allow-with-breadcrumb. Until
    # that ADR exists this test is SKIPPED, not xfailed: an xfail(strict)
    # here would stay green under EITHER implementation and hide the
    # unresolved decision.


# ===========================================================================
# #2 — symlink rejection must be depth-independent
# ===========================================================================
class Finding2SymlinkDepthTest(TestEnvContext):
    """Consensus C9. ``_find_sentinels`` rejects a symlink at ``p``,
    ``p.parent`` and ``p.parent.parent`` — hard-coded to the depth of
    ``PLAN-*/architect/round-*/approved.md``. The ``PLAN-*`` segment one
    level further up is never checked, so
    ``.claude/plans/PLAN-EVIL -> /tmp/evil`` smuggles a foreign sentinel
    into the trusted set. Re-coupling the guard to pattern depth would
    reopen the hole on the next 6-segment pattern (the dead-gate class
    this file has already suffered twice); the fix must walk every segment
    from ``p`` up to ``base``, and/or assert ``realpath(p)`` stays under
    ``realpath(base)``.

    RESIDUAL, deliberately not asserted here: a symlink at ``base``
    itself (``.claude/plans``) is covered by neither proposed form —
    walking "from p to base" excludes base, and realpath-containment still
    holds when base IS the symlink. Flagged for W2 rather than pinned,
    because pinning today's behavior there would pin a bypass.

    Note the plan-ROOT grandfather pattern (``PLAN-*/approved.md``) is
    NOT affected: for it the ``PLAN-*`` segment IS ``p.parent``.
    """

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_hook()
        self.plans = self.project_dir / ".claude" / "plans"
        self.plans.mkdir(parents=True, exist_ok=True)
        self.outside = self._tmp_root / "outside"

    def _foreign_bundle(self, name: str, nested: bool) -> Path:
        """Build a sentinel bundle OUTSIDE the repo and return its root."""
        root = self.outside / name
        leaf = root / "architect" / "round-1" if nested else root
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "approved.md").write_text(
            _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n", encoding="utf-8"
        )
        return root

    def _rels(self) -> List[str]:
        return sorted(
            str(p.relative_to(self.project_dir))
            for p in self.mod._find_sentinels(self.project_dir)
        )

    def _symlink(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target)
        except OSError:  # pragma: no cover - fs without symlink support
            self.skipTest("filesystem does not support symlinks")

    # ---- controls --------------------------------------------------------

    def test_2_control_symlinked_round_dir_is_rejected(self) -> None:
        """Positive control (always-pass): the symlink the guard DOES
        check — at ``p.parent`` — is rejected. Proves the probe is alive
        and that the repro below is measuring the missing level, not a
        broken fixture."""
        bundle = self._foreign_bundle("evil-parent", nested=False)
        arch = self.plans / "PLAN-902" / "architect"
        arch.mkdir(parents=True, exist_ok=True)
        self._symlink(arch / "round-1", bundle)
        self.assertEqual(self._rels(), [])

    def test_2_control_ordinary_sentinel_is_still_discovered(self) -> None:
        """Anti-over-block fence (always-pass, doubles as the S6
        interaction guard with #1/#10): an ordinary on-disk sentinel must
        survive the #2 fix. A containment check that rejects legitimate
        bundles would self-DoS every ceremony."""
        d = self.plans / "PLAN-903" / "architect" / "round-1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "approved.md").write_text(
            _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n", encoding="utf-8"
        )
        self.assertEqual(
            self._rels(), [".claude/plans/PLAN-903/architect/round-1/approved.md"]
        )

    # ---- repro -----------------------------------------------------------

    @_XFAIL_2
    def test_2_repro_symlinked_plan_segment_is_rejected(self) -> None:
        """DEFECT REPRO: ``.claude/plans/PLAN-901`` is a symlink to a
        directory outside the repo carrying
        ``architect/round-1/approved.md``. HEAD returns that foreign
        sentinel as trusted (its ``p``/``p.parent``/``p.parent.parent``
        are all real directories inside the link target). Post-fix the
        trusted set must be empty."""
        bundle = self._foreign_bundle("evil-plan", nested=True)
        self._symlink(self.plans / "PLAN-901", bundle)
        self.assertEqual(
            self._rels(),
            [],
            msg="foreign sentinel reached the trusted set via a symlinked "
                "PLAN-* segment",
        )


# ===========================================================================
# #3 + #8 — guard the files the guard itself trusts
# ===========================================================================
class Finding3And8GuardTheGuardfilesTest(_Plan162Base):
    """Consensus C10. The sentinel signer registry
    (``.claude/security/sentinel-signers-registry.yaml``, the ADR-121
    identity root consulted by ``_sentinel_grants_path``) and the policy
    drift manifest (``.claude/policies/.drift-manifest.json``) are guarded
    by NEITHER rail — verified on HEAD before writing this file. Unlike
    #12 there is no second layer to fall back on, so each needs its own
    red-first proof of the doubly-unguarded state.

    The fix guards the FILES on both rails. It explicitly does NOT invert
    the ``.exists()`` check into "absence implies fail-closed": that would
    require a definition of "expected" which is itself editable, and would
    make DELETING a file a way to choose the posture.
    """

    TARGETS = (
        ".claude/security/sentinel-signers-registry.yaml",
        ".claude/policies/.drift-manifest.json",
    )

    def setUp(self) -> None:
        super().setUp()
        self.hook = _load_hook()
        self.kernel = _load_kernel()
        for rel in self.TARGETS + (".claude/policies/guarded.yaml",):
            p = self.project_dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")

    def _abs(self, rel: str) -> str:
        return str(self.project_dir / rel)

    def test_3_control_guarded_neighbour_classifies_on_both_rails(self) -> None:
        """Anti-vacuity: a sibling under the SAME directory that IS
        guarded today (``.claude/policies/*.yaml``) classifies True on
        both rails, so a False below is about the pattern list, not about
        a broken repo_root."""
        neighbour = self._abs(".claude/policies/guarded.yaml")
        self.assertTrue(self.hook._is_canonical(neighbour, self.project_dir))
        self.assertTrue(self.kernel._is_kernel_path(neighbour, self.project_dir))

    @_XFAIL_3
    def test_3_repro_guardfiles_classify_on_both_rails(self) -> None:
        """DEFECT REPRO: both guard-files must classify canonical AND
        kernel. HEAD returns False on both rails for both files."""
        for rel in self.TARGETS:
            self.assertTrue(
                self.hook._is_canonical(self._abs(rel), self.project_dir),
                msg="canonical rail does not guard {0}".format(rel),
            )
            self.assertTrue(
                self.kernel._is_kernel_path(self._abs(rel), self.project_dir),
                msg="kernel rail does not guard {0}".format(rel),
            )

    @_XFAIL_3
    def test_3_repro_end_to_end_canonical_hook_blocks_guardfiles(self) -> None:
        """DEFECT REPRO end-to-end: an unsigned Edit of either guard-file
        (no sentinel present) must BLOCK on the sentinel rail."""
        for rel in self.TARGETS:
            d = self._decision(self._edit_event(self._abs(rel)))
            self.assertEqual(d.get("decision"), "block", msg="{0}: {1}".format(rel, d))
            self.assertIn(
                "CANONICAL-EDIT-BLOCKED", d.get("reason", ""),
                msg="{0}: {1}".format(rel, d),
            )

    @_XFAIL_3
    def test_3_repro_end_to_end_kernel_hook_blocks_guardfiles(self) -> None:
        """DEFECT REPRO end-to-end on the second rail: both guard-files
        must be kernel HARD-DENY (no sentinel escape) absent
        CEO_KERNEL_OVERRIDE."""
        for rel in self.TARGETS:
            d = self._decision(self._edit_event(self._abs(rel)), hook=_KERNEL_PATH)
            self.assertEqual(d.get("decision"), "block", msg="{0}: {1}".format(rel, d))
            self.assertIn(
                "ARBITRATION-KERNEL-BLOCKED", d.get("reason", ""),
                msg="{0}: {1}".format(rel, d),
            )


# ===========================================================================
# #4 — scope containment (marker tier discipline)
# ===========================================================================
class Finding4ScopeContainmentTest(_SentinelParserBase):
    """Consensus C5, narrowed. The original "parse only inside the
    markers" proposal would have bricked 31% of live sentinels (5 of 16
    carry no BEGIN marker), so the shipped fix is three narrow rules:

    1. If the BEGIN marker exists, NEVER fall back to Tier-2 — the code
       already fail-CLOSES on that principle for a marker region with an
       unparseable interior (``:1130``); a BEGIN with a missing/malformed
       END silently does the opposite today.
    2. Oversize (> ``_SCOPE_MARKER_CAP_BYTES``) must REJECT fail-closed
       instead of downgrading to the whole-file parser.
    3. The END marker must terminate a Tier-2 scope block.

    OPEN for W2, deliberately NOT asserted here: ``:1122`` compares
    ``len(text)`` in CHARACTERS against a cap named in BYTES. The
    consensus requires deciding that explicitly; writing a test for either
    reading would be inventing the contract, so the boundary case
    (chars <= cap < bytes) is left to W2 and flagged in the W1 report. The
    oversize repro below is unambiguous — it exceeds the cap under BOTH
    readings.
    """

    # ---- controls --------------------------------------------------------

    def test_4_control_wellformed_tier1_sentinel_grants(self) -> None:
        """Fixture validity (always-pass): a well-formed Tier-1 sentinel
        grants, with lifecycle text outside the markers ignored."""
        s = self._sentinel(
            "PLAN-404",
            "<!-- BEGIN SIGNED SCOPE -->\n" + _APPROVED_BY
            + "Scope:\n  - " + _TEAM_REL + "\n<!-- END SIGNED SCOPE -->\n"
            "Status: landed\n",
        )
        with self._gpg_rail():
            self.assertTrue(self.mod._sentinel_grants_path(s, _TEAM_REL))

    def test_4_control_marker_region_without_scope_fails_closed(self) -> None:
        """Always-pass PIN of the existing ``:1130`` posture: a WELL-FORMED
        marker pair whose interior declares no Scope grants nothing. This
        is the principle the two repros below say must extend to the
        malformed-marker and oversize cases."""
        s = self._sentinel(
            "PLAN-413",
            "<!-- BEGIN SIGNED SCOPE -->\n" + _APPROVED_BY
            + "Plans: PLAN-413\n<!-- END SIGNED SCOPE -->\n\n"
            "Status: lifecycle\nScope:\n  - " + _TEAM_REL + "\n",
        )
        with self._gpg_rail():
            self.assertFalse(self.mod._sentinel_grants_path(s, _TEAM_REL))

    # ---- repros ----------------------------------------------------------

    @_XFAIL_4
    def test_4_repro_begin_marker_without_end_must_not_use_tier2(self) -> None:
        """DEFECT REPRO (rule 1): a BEGIN marker with no END is an
        explicit-but-broken Owner intent signal. HEAD finds no marker
        PAIR, silently downgrades to the Tier-2 whole-file parser and
        grants. Post-fix: marker present implies never Tier-2, so this
        sentinel grants nothing."""
        s = self._sentinel(
            "PLAN-411",
            "<!-- BEGIN SIGNED SCOPE -->\n" + _APPROVED_BY
            + "Scope:\n  - " + _TEAM_REL + "\n",
        )
        with self._gpg_rail():
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="BEGIN-marker sentinel fell back to the Tier-2 parser",
            )

    @_XFAIL_4
    def test_4_repro_oversize_marker_file_rejects_fail_closed(self) -> None:
        """DEFECT REPRO (rule 2): the same sentinel shape as the
        ``..._marker_region_without_scope_fails_closed`` control — marker
        region declares no Scope, a Scope OUTSIDE the markers grants the
        target — but padded past the cap. HEAD skips Tier-1 on size and
        the Tier-2 parser grants what the marker region fail-CLOSES. The
        twin control proves the only difference is the size."""
        pad = "\n".join("pad line {0}".format(i) for i in range(8000))
        s = self._sentinel(
            "PLAN-412",
            "<!-- BEGIN SIGNED SCOPE -->\n" + _APPROVED_BY
            + "Plans: PLAN-412\n" + pad + "\n<!-- END SIGNED SCOPE -->\n\n"
            "Status: lifecycle\nScope:\n  - " + _TEAM_REL + "\n",
        )
        self.assertGreater(
            len(s.read_text(encoding="utf-8")),
            self.mod._SCOPE_MARKER_CAP_BYTES,
            msg="fixture is not actually oversize",
        )
        with self._gpg_rail():
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="oversize sentinel silently downgraded to Tier-2",
            )

    @_XFAIL_4
    def test_4_repro_end_marker_terminates_tier2_scope(self) -> None:
        """DEFECT REPRO (rule 3): a legacy (marker-less) sentinel whose
        Scope block is followed by an END marker and then more bullets.
        ``_SCOPE_TERMINATOR_RE`` does not know the marker, the comment
        line is not bullet-shaped so collection simply continues, and the
        post-END bullet grants on HEAD."""
        s = self._sentinel(
            "PLAN-403",
            _APPROVED_BY + "Scope:\n  - .claude/unrelated.md\n"
            "<!-- END SIGNED SCOPE -->\n  - " + _TEAM_REL + "\n",
        )
        with self._gpg_rail():
            self.assertFalse(
                self.mod._sentinel_grants_path(s, _TEAM_REL),
                msg="bullet after the END marker was collected into Scope",
            )


# ===========================================================================
# #5a / #5b — failure posture (PIN + repro)
# ===========================================================================
class Finding5FailurePostureTest(_Plan162Base):
    """Consensus C4. The council's "ADR-010 mandates fail-open" citation
    is FALSE (zero occurrences in the ADR); the only such text is the
    hook's own docstring, so the finding splits:

    * **5a — ACCEPT.** ``read_event`` RAISING is a genuine infrastructure
      failure and stays fail-open; the kernel sibling is fail-open
      identically here. Pinned below (passes today and must keep passing).
    * **5b — FIX.** ``event.parse_error`` is by name and construction the
      signal that the PAYLOAD did not parse. CLAUDE.md §4 is literal
      ("fail-closed on INPUT"), the kernel already implements the
      precedent form, and this hook is the drift.

    The pin is obligatory either way: ``grep parse_error`` across the
    hook's eight test files returns ZERO — the contract is fixed by no
    test in EITHER direction today.
    """

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()

    def test_5a_pin_read_event_exception_still_allows(self) -> None:
        """PIN (always-pass, both before and after W2): an EXCEPTION out
        of ``read_event`` is INFRA, not input, and must keep fail-opening.
        A 5b fix that over-corrects into blocking infrastructure faults
        turns this pin red.

        Driven in-process: the fault is a monkeypatch on the resolved
        adapter module, impossible to stage on stdin (a malformed payload
        produces ``parse_error``, which is 5b's surface, not 5a's)."""
        mod = _load_hook()
        from _lib.adapters import claude as _claude_adapter

        def _boom(*_args, **_kwargs):
            raise RuntimeError("PLAN-162 injected: adapter read_event fault")

        stdout = io.StringIO()
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(_claude_adapter, "read_event", _boom), \
                mock.patch("sys.stdin", io.StringIO("{}")), \
                contextlib.redirect_stdout(stdout):
            rc = mod.main()

        self.assertEqual(rc, 0)
        out = stdout.getvalue().strip()
        self.assertTrue(out, msg="ZERO-EMIT on the infra fail-open path")
        d = json.loads(out.splitlines()[-1])
        self.assertNotEqual(
            d.get("decision"),
            "block",
            msg="5a regression: an INFRA fault now fail-CLOSES: {0}".format(d),
        )

    @_XFAIL_5B
    def test_5b_repro_parse_error_must_block(self) -> None:
        """DEFECT REPRO: a malformed stdin payload sets
        ``event.parse_error`` and HEAD emits a bare allow. The edit class
        this hook guards cannot be verified against an unparseable
        payload, so it must fail-CLOSED.

        The exact reason_code is W2's to choose (the kernel's precedent
        wording is "payload parse error"); this test asserts only the
        decision and that a reason is carried, so the fix is not
        over-specified."""
        d = self._decision_raw("{ this is not valid json")
        self.assertEqual(
            d.get("decision"),
            "block",
            msg="parse_error allowed the edit-class event: {0}".format(d),
        )
        self.assertTrue(d.get("reason"), msg="block carried no reason: {0}".format(d))

    def test_5b_control_wellformed_payload_is_unaffected(self) -> None:
        """Anti-over-block fence (always-pass): a well-formed payload for
        a NON-canonical path must keep being allowed. A 5b fix that blocks
        on any payload it dislikes turns this red."""
        d = self._decision(self._edit_event(str(self.project_dir / "docs/notes.md")))
        self.assertNotEqual(d.get("decision"), "block", msg=d)


# ===========================================================================
# #7 — file:// URI candidates
# ===========================================================================
class Finding7FileUriTest(_Plan162Base):
    """Consensus (deferred list, FIX kept). ``uri`` is one of
    ``_MCP_WRITE_PATH_KEYS``, but a ``file://`` value is handed to
    ``Path()`` verbatim: it becomes a RELATIVE path whose first segment is
    ``file:``, resolves against the CWD, lands outside the repo root and
    classifies non-canonical — so the edit sails through ungated.

    W1 leaves the FORM to W2: normalize the scheme inside
    ``_extract_mcp_target_paths`` (one function), or treat an
    un-interpretable value as fail-CLOSED. Both lanes accept either; these
    tests assert only the OUTCOME, so either form satisfies them.
    """

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()
        self.target_abs = str(self.project_dir / _TEAM_REL)

    def test_7_control_plain_path_under_uri_key_is_gated(self) -> None:
        """Anti-vacuity (always-pass): the ``uri`` key IS wired into
        candidate extraction — a plain absolute path there already
        blocks. So a False below is about the scheme, not the key."""
        d = self._decision(self._mcp_event({"uri": self.target_abs, "content": "x"}))
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn(_TEAM_REL, d.get("reason", ""), msg=d)

    def test_7_control_non_canonical_file_uri_stays_allowed(self) -> None:
        """Anti-over-block fence (always-pass): a ``file://`` URI for a
        NON-canonical path must still be allowed after the fix."""
        uri = "file://" + str(self.project_dir / "docs" / "notes.md")
        d = self._decision(self._mcp_event({"uri": uri, "content": "x"}))
        self.assertNotEqual(d.get("decision"), "block", msg=d)

    @_XFAIL_7
    def test_7_repro_file_uri_target_is_gated(self) -> None:
        """DEFECT REPRO: ``file:///…/.claude/team.md`` with no sentinel
        must BLOCK naming the path. HEAD classifies it non-canonical and
        allows."""
        uri = "file://" + self.target_abs
        d = self._decision(self._mcp_event({"uri": uri, "content": "x"}))
        self.assertEqual(d.get("decision"), "block", msg=d)
        self.assertIn(_TEAM_REL, d.get("reason", ""), msg=d)


# ===========================================================================
# #9 — blocked_tool must be forensic, not decorative
# ===========================================================================
class Finding9BlockedToolForensicTest(_Plan162Base):
    """Consensus C6. Four sites write ``blocked_tool`` into the HMAC audit
    chain: three carry the literal ``"Edit|Write|MultiEdit"`` regardless of
    which tool actually fired, and one carries ``""``. A human reading the
    chain after an incident is told the wrong tool. The fix plumbs
    ``event.tool_name`` through — VALIDATED against a closed enum / the
    ``^mcp__[a-z0-9_]+$`` shape first, so the fix does not inject
    attacker-influenced text into a log humans read.

    Two of the four sites (the session-roots deny and the registry-tamper
    emit) require a corrupt session-roots registry plus an external write
    target to reach; they are covered by the SOURCE-level fence rather
    than by a behavioral test each — the fence is mechanical and covers
    all four at once.
    """

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()
        self.target_abs = str(self.project_dir / _TEAM_REL)

    def test_9_control_veto_event_is_emitted(self) -> None:
        """Anti-vacuity (always-pass): the block DOES reach the audit log
        in this harness. Without it, a ``blocked_tool`` assertion could
        pass or fail for reasons that have nothing to do with #9."""
        d = self._decision(self._mcp_event({"path": [self.target_abs], "content": "x"}))
        self.assertEqual(d.get("decision"), "block", msg=d)
        events = self._veto_events()
        self.assertTrue(events, msg="no veto_triggered event in the audit log")
        self.assertIn(
            "canonical_edit_unsigned", [e.get("reason_code") for e in events]
        )

    def test_9_pin_hostile_tool_name_never_lands_verbatim(self) -> None:
        """PIN (always-pass, before and after W2): a hostile ``tool_name``
        must never reach the audit field verbatim. It passes today only
        because the field is a hardcoded literal — the point is that it
        must STILL pass once the field becomes event-derived. This is the
        half of #9 that turns a forensics fix into an injection vector if
        it ships unvalidated."""
        hostile = 'mcp__evil\n{"action":"forged_event","hook":"pwned"}'
        d = self._decision(
            self._mcp_event(
                {"path": [self.target_abs], "content": "x"}, tool_name=hostile
            )
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        for ev in self._veto_events():
            recorded = str(ev.get("blocked_tool", ""))
            self.assertNotIn("forged_event", recorded)
            self.assertNotIn("\n", recorded)

    @_XFAIL_9
    def test_9_repro_audit_records_the_event_tool_name(self) -> None:
        """DEFECT REPRO: the blocked event fired ``mcp__future__bulk_write``
        but the audit chain records ``Edit|Write|MultiEdit``."""
        tool = "mcp__future__bulk_write"
        d = self._decision(
            self._mcp_event({"path": [self.target_abs], "content": "x"}, tool_name=tool)
        )
        self.assertEqual(d.get("decision"), "block", msg=d)
        recorded = [
            e.get("blocked_tool")
            for e in self._veto_events()
            if e.get("reason_code") == "canonical_edit_unsigned"
        ]
        self.assertTrue(recorded, msg="no canonical_edit_unsigned event emitted")
        self.assertIn(
            tool,
            recorded,
            msg="audit chain recorded {0!r} for a {1} event".format(recorded, tool),
        )

    @_XFAIL_9
    def test_9_repro_source_carries_no_hardcoded_blocked_tool(self) -> None:
        """DEFECT REPRO, SOURCE-level fence over ALL FOUR sites at once
        (two of which are not economically reachable from this surface).
        A behavioral test can only prove the site it reaches; this proves
        no site was left behind."""
        for literal in ('blocked_tool="Edit|Write|MultiEdit"', 'blocked_tool=""'):
            self.assertNotIn(
                literal,
                _HOOK_SOURCE,
                msg="hardcoded {0} still present in {1}".format(literal, _HOOK_PATH),
            )


# ===========================================================================
# S2 — the sentinel set is a trust anchor and is not guarded
# ===========================================================================
@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
class S2SentinelUnderEnvOverrideTest(_Plan162Base):
    """Consensus S2. ``.claude/plans/PLAN-*/**/approved.md`` is guarded by
    neither rail, and under an Owner ``CEO_SENTINEL_UNLOCK`` window
    ``:994`` skips the GPG rail entirely — so an ``approved.md`` the AGENT
    writes during that window GRANTS. That is a bypass of AUTHORIZATION,
    not merely a denial-of-service on the gate's cost.

    **Mitigation CORRECTED by pair-rail R2 (P1).** The consensus first
    wrote the rule as "tracked in git OR pre-existing at session start".
    That disjunction is defeatable and the codex proved it: inside the
    unlock window the agent writes ``approved.md`` and then runs an
    ordinary ``git add`` (or ``git commit``) — ``git ls-files
    --error-unmatch`` now reports it TRACKED, and a HEAD-based check would
    accept an agent-authored commit just the same. Git state is a
    statement about the index, not about who authorized the file.

    The trust anchor is therefore **session start, not git state**: under
    ``env_override``, accept only sentinels that already existed when the
    session began. The tests below express that as a repo-anchor sha the
    fix MUST honor (``CEO_SESSION_ANCHOR_SHA`` here is a proposed
    interface name, not an existing one — W2 may rename it, but it may
    not drop the requirement). Three negatives are required, one per way
    the agent can dress a fresh file up as legitimate: untracked, staged,
    committed.
    """

    UNLOCK = {
        "CEO_SENTINEL_UNLOCK": "PLAN-162-w1-instrument",
        "CEO_SENTINEL_UNLOCK_ACK": "I-ACCEPT",
    }

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()
        self._git("init", "-q")
        self._git("config", "user.email", "plan162@example.invalid")
        self._git("config", "user.name", "plan162")
        self._git("config", "commit.gpgsign", "false")
        self.sentinel = self._write_sentinel("PLAN-701", [_TEAM_REL])
        self.payload = self._edit_event(str(self.project_dir / _TEAM_REL))

    def _git(self, *args: str):
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def _is_tracked(self) -> bool:
        rel = str(self.sentinel.relative_to(self.project_dir))
        return self._git("ls-files", "--error-unmatch", rel).returncode == 0

    def _anchor_env(self) -> dict:
        """Commit the sentinel and return env naming THAT commit as the
        session anchor — i.e. the sentinel predates the session."""
        self._git("add", "-A")
        self.assertEqual(self._git("commit", "-q", "-m", "sentinel").returncode, 0)
        sha = self._git("rev-parse", "HEAD").stdout.strip()
        env = dict(self.UNLOCK)
        env["CEO_SESSION_ANCHOR_SHA"] = sha
        return env

    def test_s2_control_sentinel_predating_session_still_grants(self) -> None:
        """Anti-self-DoS control (always-pass): a sentinel that existed at
        session start MUST keep granting under the unlock window, or the
        fix degrades into 'env_override never grants' — the self-DoS the
        debate rejected when it removed the sentinel cap.

        Note this control commits the sentinel and then names THAT commit
        as the anchor, so the sentinel genuinely predates the session
        boundary. It is not the same shape as the defect repros below,
        where the anchor is taken FIRST and the sentinel appears after."""
        d = self._decision(self.payload, env_extra=self._anchor_env())
        self.assertNotEqual(d.get("decision"), "block", msg=d)
        self.assertIn("PLAN-701", d.get("systemMessage", ""), msg=d)

    @_XFAIL_S2
    def test_s2_repro_staged_in_session_sentinel_does_not_grant(self) -> None:
        """DEFECT REPRO (pair-rail R2 P1, first of the two git-dressing
        forms): the agent writes the sentinel during the unlock window and
        runs ``git add``. ``git ls-files --error-unmatch`` now calls it
        TRACKED — so any fix keyed on git-tracked-ness accepts it. The
        anchor is taken BEFORE the sentinel exists, so a session-anchored
        fix must still block."""
        empty = self.project_dir / ".gitkeep"
        empty.write_text("", encoding="utf-8")
        self._git("add", ".gitkeep")
        self._git("commit", "-q", "-m", "anchor before the sentinel exists")
        anchor = self._git("rev-parse", "HEAD").stdout.strip()
        self._git("add", "-A")  # the agent stages its own approved.md
        self.assertTrue(self._is_tracked(), msg="fixture: sentinel not staged")
        env = dict(self.UNLOCK)
        env["CEO_SESSION_ANCHOR_SHA"] = anchor
        d = self._decision(self.payload, env_extra=env)
        self.assertEqual(
            d.get("decision"), "block",
            msg="a sentinel STAGED by the agent after session start granted "
                "under env_override: {0}".format(d),
        )

    @_XFAIL_S2
    def test_s2_repro_committed_in_session_sentinel_does_not_grant(self) -> None:
        """DEFECT REPRO (pair-rail R2 P1, second form): the agent goes all
        the way and COMMITS its own sentinel inside the window. A
        HEAD-based check accepts it — an agent-authored commit is still an
        agent-authored file. Only the session anchor separates them."""
        empty = self.project_dir / ".gitkeep"
        empty.write_text("", encoding="utf-8")
        self._git("add", ".gitkeep")
        self._git("commit", "-q", "-m", "anchor before the sentinel exists")
        anchor = self._git("rev-parse", "HEAD").stdout.strip()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "agent commits its own sentinel")
        env = dict(self.UNLOCK)
        env["CEO_SESSION_ANCHOR_SHA"] = anchor
        d = self._decision(self.payload, env_extra=env)
        self.assertEqual(
            d.get("decision"), "block",
            msg="a sentinel COMMITTED by the agent after session start "
                "granted under env_override: {0}".format(d),
        )

    @_XFAIL_S2
    def test_s2_repro_untracked_in_session_sentinel_does_not_grant(self) -> None:
        """DEFECT REPRO: the sentinel is UNTRACKED and was created during
        this session. Under ``CEO_SENTINEL_UNLOCK`` HEAD grants the
        canonical edit on the strength of a plaintext file the agent
        itself could have written."""
        self.assertFalse(self._is_tracked(), msg="fixture: sentinel is tracked")
        d = self._decision(self.payload, env_extra=self.UNLOCK)
        self.assertEqual(
            d.get("decision"),
            "block",
            msg="untracked in-session sentinel granted under env_override: "
                "{0}".format(d),
        )


# ===========================================================================
# S6 — interaction pass between findings
# ===========================================================================
class InteractionPassTest(_Plan162Base):
    """Consensus S6. Two fixes in this pack meet each other on the same
    event, and this file's own history includes an interaction bug
    (``SentinelCacheKeyRegressionTest``), so W1 budgets an explicit pass.
    """

    def setUp(self) -> None:
        super().setUp()
        self._make_repo_layout()
        self.mod = _load_hook()
        self.target_abs = str(self.project_dir / _TEAM_REL)

    def test_interaction_2x1_legit_sentinel_survives_alongside_symlink(self) -> None:
        """#2 x #1/#10 (always-pass): the #2 fix narrows what
        ``_find_sentinels`` returns, which is the input set the cache
        partition keys on. A legitimate sentinel standing next to a
        rejected symlinked one must still be discovered AND still grant —
        otherwise the #2 fix silently inverts the #1 fixtures.

        The grant half is driven through the STUBBED signature rail, not
        through ``CEO_SENTINEL_UNLOCK``: an unlock-based fixture would be
        invalidated by the S2 fix in this same pack (untracked in-session
        sentinels stop granting under env_override), which is itself an
        interaction worth naming."""
        plans = self.project_dir / ".claude" / "plans"
        legit_dir = plans / "PLAN-801" / "architect" / "round-1"
        legit_dir.mkdir(parents=True, exist_ok=True)
        legit = legit_dir / "approved.md"
        legit.write_text(
            _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n", encoding="utf-8"
        )
        (legit_dir / "approved.md.asc").write_text("PLAN162-SIG", encoding="utf-8")
        foreign = self._tmp_root / "foreign" / "architect" / "round-1"
        foreign.mkdir(parents=True, exist_ok=True)
        (foreign / "approved.md").write_text(
            _APPROVED_BY + "Scope:\n  - " + _TEAM_REL + "\n", encoding="utf-8"
        )
        try:
            (plans / "PLAN-802").symlink_to(self._tmp_root / "foreign")
        except OSError:  # pragma: no cover - fs without symlink support
            self.skipTest("filesystem does not support symlinks")

        found = self.mod._find_sentinels(self.project_dir)
        self.assertIn(
            ".claude/plans/PLAN-801/architect/round-1/approved.md",
            [str(p.relative_to(self.project_dir)) for p in found],
            msg="the legitimate sentinel was lost",
        )
        self.mod._SENTINEL_VERIFY_CACHE.clear()
        try:
            with mock.patch.multiple(
                self.mod,
                _gpg_verify=_GpgStub(),
                _SENTINEL_SIGNERS_REGISTRY_YAML=self._tmp_root / "absent.yaml",
            ):
                self.assertTrue(
                    self.mod._sentinel_grants_path(legit, _TEAM_REL),
                    msg="the legitimate sentinel stopped granting",
                )
        finally:
            self.mod._SENTINEL_VERIFY_CACHE.clear()

    @_XFAIL_7X9
    def test_interaction_7x9_uri_block_records_rel_and_tool(self) -> None:
        """#7 x #9 on the SAME event: once ``file://`` candidates are
        gated (#7), the block they produce writes the #9 forensic field.
        The breadcrumb must carry the repo-relative canonical path — never
        the raw URI, which is attacker-shaped input — together with the
        validated event tool name. Fails on HEAD at the first hurdle: the
        event is not blocked at all, so no breadcrumb exists."""
        tool = "mcp__future__bulk_write"
        uri = "file://" + self.target_abs
        d = self._decision(self._mcp_event({"uri": uri, "content": "x"}, tool_name=tool))
        self.assertEqual(d.get("decision"), "block", msg=d)
        events = [
            e for e in self._veto_events()
            if e.get("reason_code") == "canonical_edit_unsigned"
        ]
        self.assertTrue(events, msg="no canonical_edit_unsigned breadcrumb")
        for ev in events:
            self.assertEqual(ev.get("blocked_tool"), tool, msg=ev)
            self.assertNotIn("file://", str(ev.get("reason_preview", "")), msg=ev)
            self.assertIn(_TEAM_REL, str(ev.get("reason_preview", "")), msg=ev)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
