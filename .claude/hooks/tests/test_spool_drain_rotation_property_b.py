"""PLAN-112-FOLLOWUP-hmac-tamper-fix AC13/AC14 — stdlib property canary (F-7.7).

> **Regression for PLAN-112-FOLLOWUP-hmac-tamper-fix F-7.7; do NOT remove.**
> (AC14 R9 fold — the deterministic reproducer
> `test_spool_drain_rotation_race.py` could be deleted accidentally after the
> fix; this property loop is the additional canary that keeps the bug from
> recurring silently.)

This is the AC13 "property test (N=50 scenarios)" companion to the single
deterministic reproducer in ``test_spool_drain_rotation_race.py``. Where the
deterministic test pins ONE hand-tuned scenario, this loop fuzzes the
parameters that govern the Phase 4↔Phase 5 spool-drain rotation race:

  - ``n_pre``    — number of pre-populate sync emits (sets canonical pre_size)
  - ``threshold``— rotation byte threshold placed BETWEEN the expected
                   post-rotation size and ``pre_size`` (forces a rotation on
                   the first drain probe)
  - ``n_spool``  — number of entries spooled then drained across the boundary

**Invariant under test (the F-7.7 canary):** for every randomized scenario,
after ``drain_now(force=True)`` the active canonical log VERIFIES INTACT —
the verifier reaches the end of the chain rather than reporting a spurious
``STATUS_TAMPER`` at line 1. When a rotation fired, line 1 must additionally
be the ``chain_reset_marker`` (Wave B.3 contract). Pre-Wave-B.1 (the producer
hoist of ``_rotate_if_needed_safe`` into Phase 4), randomized scenarios that
crossed a rotation boundary produced STATUS_TAMPER; post-fix they are intact.

**Stdlib-only methodology (PLAN-087 D.3 precedent —
``test_audit_hmac_chain_monotonicity_property.py``):** ``random.Random(SEED)``
for deterministic reproducibility (no CI flake surface), N=50 bounded
iterations, NO ``hypothesis`` import (rejected framework-wide per ADR-126
§Part 5 / boundary_test; the dep lives only in the c5-dev-tools sidecar).

**Trade-off documented:** the fixed-seed loop loses (a) automated shrinking
of a failing counter-example — the operator inspects the printed scenario
params manually — and (b) coverage-guided generation. ACCEPTABLE: the failure
surface is the rotation-boundary chaining state, amply exercised by 50
fixed-seed scenarios that each independently force a rotation. No ADR
exception or framework dependency added.

Reference: PLAN-112 F-7.7 (C10 + D3); PLAN-113 C5 set-A item #1.
"""

from __future__ import annotations

import importlib
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_HOOKS = Path(__file__).resolve().parent.parent
if str(_REPO_HOOKS) not in sys.path:
    sys.path.insert(0, str(_REPO_HOOKS))


class SpoolDrainRotationPropertyCanary(unittest.TestCase):
    """N=50 seeded spool-drain-across-rotation scenarios — chain stays intact.

    AC13/AC14 — stdlib-only, ``random.Random(91)`` deterministic, no hypothesis.
    """

    # Fixed seed → deterministic across CI runs (no flake). 91 is arbitrary
    # but distinct from the D.3 monotonicity canary's seed 42.
    SEED = 91
    ITERATIONS = 50

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="plan-112-followup-prop-b-"))
        # Save the full env contract this test mutates (mirrors the
        # deterministic SpoolDrainPathRotationRaceTest env handling).
        self._saved = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_DIR",
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_LOG_ROTATE_BYTES",
                "CEO_AUDIT_SYNC_MODE",
                "CEO_PROJECT_STATE_DIR",
            )
        }

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        shutil.rmtree(self.base, ignore_errors=True)

    @staticmethod
    def _reload_audit():
        """Reload audit_hmac then audit_emit (emit imports hmac) honoring env.

        Uses import_module+reload (not a stale module global) so it survives a
        prior test in the same process having rebound sys.modules under a
        divergent sys.path — same robustness guard as the deterministic test.
        """
        ah = importlib.reload(importlib.import_module("_lib.audit_hmac"))
        ae = importlib.reload(importlib.import_module("_lib.audit_emit"))
        return ah, ae

    def _run_scenario(self, i: int, rng: random.Random) -> bool:
        """Run one randomized spool-drain-across-rotation scenario.

        Returns True if a rotation fired (for the suite-level sanity counter).
        Asserts the F-7.7 invariant (verify_chain INTACT) regardless.
        """
        iter_dir = self.base / "s{:02d}".format(i)
        iter_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(iter_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(iter_dir / "audit-log.jsonl")
        os.environ["CEO_PROJECT_STATE_DIR"] = str(iter_dir)

        # --- Step 1: pre-populate the canonical log via sync emits at a HIGH
        # threshold so no rotation fires yet. n_pre varies pre_size. ---
        n_pre = rng.randint(4, 9)
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "100000"  # 100KB — no rotation
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        ah, ae = self._reload_audit()

        for k in range(n_pre):
            ae.emit_plan_transition(
                plan_id="PRE-{:02d}-{:02d}".format(i, k),
                from_status="draft",
                to_status="reviewed",
                file_path=".claude/plans/PRE-{:02d}-{:02d}.md".format(i, k),
                session_id="prop-b-pre",
                project="test",
            )

        log_path = ae._log_path()
        self.assertTrue(log_path.exists(), "scenario {}: pre-populate failed".format(i))
        pre_size = log_path.stat().st_size

        # --- Step 2: place the threshold BETWEEN the expected post-rotation
        # size (marker ~500B + small batch) and pre_size, so the first drain
        # probe MUST rotate but Phase 5 won't immediately re-rotate. ---
        threshold = max(1500, pre_size - rng.randint(300, 700))
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = str(threshold)
        os.environ.pop("CEO_AUDIT_SYNC_MODE", None)  # exercise the SPOOL path
        ah, ae = self._reload_audit()
        spool_writer = importlib.reload(importlib.import_module("_lib.spool_writer"))
        spool_writer._reset_caches_for_test()

        # --- Step 3: spool a small batch (NOT sync emit) ---
        n_spool = rng.randint(1, 2)
        for k in range(n_spool):
            spool_writer.spool_append(
                {
                    "action": "plan_transition",
                    "plan_id": "SPOOL-{:02d}-{:02d}".format(i, k),
                    "from_status": "draft",
                    "to_status": "reviewed",
                    "editor_tool": "Edit",
                    "file_path": ".claude/plans/SPOOL-{:02d}-{:02d}.md".format(i, k),
                    "transition_legal": True,
                    "session_id": "prop-b-spool",
                    "project": "test",
                    "event_schema": "v2",
                    "ts": "2026-05-25T12:00:00Z",
                    "tokens_in": None,
                    "tokens_out": None,
                    "tokens_total": None,
                }
            )

        # --- Step 4: force the drain across the rotation boundary ---
        spool_writer.drain_now(force=True)

        archives = list(iter_dir.glob("audit-log-*.jsonl"))
        rotated = len(archives) >= 1

        if rotated:
            # Wave B.3 contract: line 1 of the new active log is the marker.
            with log_path.open(encoding="utf-8") as f:
                line_1 = json.loads(f.readline())
            self.assertEqual(
                line_1.get("action"),
                "chain_reset_marker",
                "scenario {} (n_pre={}, n_spool={}, pre_size={}, thr={}): "
                "line 1 of post-rotation log must be chain_reset_marker; "
                "got {}".format(
                    i, n_pre, n_spool, pre_size, threshold, line_1.get("action")
                ),
            )

        # --- The F-7.7 canary: the chain verifies INTACT (verifier reaches
        # the end), whether or not a rotation fired this scenario. ---
        result = ah.verify_chain(log_path)
        self.assertEqual(
            result.status,
            ah.STATUS_INTACT,
            "F-7.7 REGRESSION at scenario {} (n_pre={}, n_spool={}, "
            "pre_size={}, threshold={}, rotated={}): verifier reports "
            "status={} instead of INTACT. The Wave B.1 Phase-4 rotation-probe "
            "hoist may have regressed.".format(
                i, n_pre, n_spool, pre_size, threshold, rotated, result.status
            ),
        )
        return rotated

    def test_spool_drain_rotation_chain_intact_property(self) -> None:
        """N=50 seeded scenarios: spool drain across rotation never tampers."""
        rng = random.Random(self.SEED)
        rotations_observed = 0
        for i in range(self.ITERATIONS):
            rotations_observed += 1 if self._run_scenario(i, rng) else 0

        # Sanity: the property must actually EXERCISE the rotation path it
        # claims to canary — otherwise a parameter-drift could silently turn
        # this into a no-rotation no-op that always passes.
        self.assertGreater(
            rotations_observed,
            0,
            "property canary never triggered a rotation across {} scenarios — "
            "the threshold/pre_size tuning drifted and the F-7.7 boundary is "
            "no longer exercised".format(self.ITERATIONS),
        )


if __name__ == "__main__":
    unittest.main()
