"""PLAN-164 W1 — pair-rail timeout cross-layer invariant (consensus C2).

Root cause being closed (measured, not inferred — see
`.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md` and
`.claude/plans/PLAN-164/debate/round-1/consensus.md`): the hook-internal
default `CEO_PAIR_RAIL_TIMEOUT_S=30s` sits BELOW the real codex verdict
latency (N=9 probe: p95 ~75s), so 12/12 historical `pair_rail_case`
events were F/TIMEOUT. The ratified fix is layered: internal default
180s, harness registration timeout 210s, with an invariant margin of
>= 30s between the layers so the harness never kills the hook before the
hook's own subprocess cap fires, plus a `statusMessage` on the
registration so the operator sees WHY a canonical edit stalls.

(The ratified pair was 120/150 under PLAN-164; ADR-110-AMEND-2 ran the
AMEND-1 §3 recalibration and moved it to 180/210 — 25.9 % of joined
post-uplift reviews sat AT OR ABOVE the 120s budget, which puts the true
p95 >= 120 by count, and the folga convention over that yields 180. The
margin stays 30s and the invariant holds at equality: 210 == 180 + 30.)

This test pins the INVARIANT BETWEEN LAYERS **and** the ratified
absolute values:

  1. kernel registration timeout (`.claude/settings.json`) equals the
     template registration timeout
     (`templates/settings/settings.base.json`) — the S283/S275 derived-
     surface-drift class;
  2. each registration timeout >= hook-internal default + 30s margin;
  3. `statusMessage` is present on the pair-rail registration in BOTH
     files;
  4. the ABSOLUTE ratified values hold: internal default == 180 (the env
     seam AND both fallback literals `timeout_s = 180.0`), registration
     == 210 in both files. A deliberate recalibration (ADR-110-AMEND-2
     trigger: censoring rate > 5 % over n >= 20 post-change reviews —
     the AMEND-1 p95-of-healthy trigger is retired as unestimable under
     right-censoring) must edit THIS test in the same change — that is
     the contract, not an inconvenience. Without (4), a unilateral
     downward drift of the internal default (e.g. 180 -> 50) stays green
     under (2) alone (210 >= 50+30) and silently re-admits the
     sub-latency class this plan retires (grok r1 MED / codex r1 MED-3).

RED-FIRST contract (staged with the rail-pack): against the pre-pack
live tree — registration timeout 60, internal default "30", NO
statusMessage — assertions (3) and (4) FAIL ((1) and (2) are
vacuously green at 60/60/30: 60 >= 30+30). The test goes fully green
only after the rail-pack applies (overlay-clone verification proves it),
and from then on any future drift that shrinks the margin or splits
kernel from template goes red.

Repo-root resolution walks parents of ``__file__`` until it finds a
COMPLETE tree (settings.json + template + hook), so the same file works
from the staged path (resolves the live repo), from an overlay clone,
and from its final home at `.claude/hooks/tests/`.

stdlib-only (json, re, pathlib, unittest). Python >= 3.9.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Tuple


def _resolve_repo_root() -> Path:
    """First parent of this file that holds the full trio of artifacts.

    Requiring all three (not just `.claude/settings.json`) means a
    PARTIAL staged subtree between this file and the real root can
    never be mistaken for the repo — the walk keeps climbing until it
    reaches a tree where every extraction target exists.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (
            (parent / ".claude" / "settings.json").is_file()
            and (parent / "templates" / "settings" / "settings.base.json").is_file()
            and (parent / ".claude" / "hooks" / "check_pair_rail.py").is_file()
        ):
            return parent
    raise RuntimeError(
        "test_pair_rail_timeout_invariant: no parent of __file__ contains "
        ".claude/settings.json + templates/settings/settings.base.json + "
        ".claude/hooks/check_pair_rail.py — cannot locate a complete repo root"
    )


_REPO_ROOT = _resolve_repo_root()
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_KERNEL_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_TEMPLATE_SETTINGS = _REPO_ROOT / "templates" / "settings" / "settings.base.json"
_HOOK_SOURCE = _HOOKS_DIR / "check_pair_rail.py"

# Ratified invariant floor (PLAN-164 debate round-1 consensus C2): the
# harness registration must outlive the hook's own subprocess cap by at
# least this many seconds, so the hook — not the harness — owns the
# timeout arm (case F stays diagnosable instead of a silent hook kill).
_MARGIN_S = 30

# Ratified ABSOLUTE values (ADR-110-AMEND-2, S291 ceremony 2026-08-03 —
# the AMEND-1 §3 recalibration ran and pointed upward: 25.9 % of joined
# post-uplift reviews sat at or above the 120 s budget, so 1.5x p95 under
# the AMEND-1 folga convention lands on 180, with the registration at
# 180 + the 30 s inter-layer margin. Was 120/150 under PLAN-164 OQ1/OQ2,
# Owner tie-break 2026-07-29.) Edit these constants ONLY together with the
# hook + both settings surfaces, in a governed change.
_RATIFIED_INTERNAL_S = 180
_RATIFIED_REGISTRATION_S = 210

# The two parse-error/clamp-reset fallbacks in check_pair_rail.py
# (`timeout_s = <N>.0`) must carry the SAME ratified internal value.
_FALLBACK_RE = re.compile(r"timeout_s = (\d+)\.0")

# The exact seam in check_pair_rail.py that defines the internal default
# (single source: `float(os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "<N>"))`).
_INTERNAL_DEFAULT_RE = re.compile(
    r'os\.environ\.get\("CEO_PAIR_RAIL_TIMEOUT_S",\s*"(\d+)"\)'
)


def _extract_internal_default_s(hook_source: Path) -> int:
    matches = _INTERNAL_DEFAULT_RE.findall(
        hook_source.read_text(encoding="utf-8")
    )
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly ONE CEO_PAIR_RAIL_TIMEOUT_S default seam in "
            "%s, found %d — the extraction regex must track the hook"
            % (hook_source, len(matches))
        )
    return int(matches[0])


def _pair_rail_registrations(settings_path: Path) -> List[Tuple[str, Dict]]:
    """Every hook dict in `settings_path` whose command runs check_pair_rail.py."""
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    found: List[Tuple[str, Dict]] = []
    for event, entries in (data.get("hooks") or {}).items():
        for entry in entries or []:
            for hook in entry.get("hooks") or []:
                if "check_pair_rail.py" in str(hook.get("command", "")):
                    found.append((event, hook))
    return found


def _sole_registration(settings_path: Path) -> Dict:
    regs = _pair_rail_registrations(settings_path)
    if len(regs) != 1:
        raise AssertionError(
            "expected exactly ONE check_pair_rail.py registration in %s, "
            "found %d" % (settings_path, len(regs))
        )
    return regs[0][1]


class TestPairRailTimeoutInvariant(TestEnvContext):
    """C2: kernel==template, registration >= internal+30s, statusMessage."""

    def setUp(self) -> None:
        super().setUp()
        self.kernel_hook = _sole_registration(_KERNEL_SETTINGS)
        self.template_hook = _sole_registration(_TEMPLATE_SETTINGS)
        self.internal_default_s = _extract_internal_default_s(_HOOK_SOURCE)

    # -- extraction sanity -------------------------------------------------

    def _registration_timeout(self, hook: Dict, origin: str) -> float:
        timeout = hook.get("timeout")
        self.assertIsInstance(
            timeout,
            (int, float),
            "pair-rail registration in %s has no numeric 'timeout' field "
            "(got %r) — the harness would fall back to its global default "
            "and the layered-timeout contract is unpinned" % (origin, timeout),
        )
        return float(timeout)

    # -- invariant 1: kernel == template (derived-surface drift class) -----

    def test_kernel_registration_timeout_equals_template(self) -> None:
        kernel_s = self._registration_timeout(self.kernel_hook, "kernel")
        template_s = self._registration_timeout(self.template_hook, "template")
        self.assertEqual(
            kernel_s,
            template_s,
            "pair-rail registration timeout drifted between the dogfood "
            "kernel (.claude/settings.json: %r) and the adopter template "
            "(templates/settings/settings.base.json: %r) — fix BOTH "
            "surfaces in the same change" % (kernel_s, template_s),
        )

    # -- invariant 2: registration >= internal default + margin ------------

    def test_registration_outlives_internal_default_by_margin(self) -> None:
        for origin, hook in (
            ("kernel", self.kernel_hook),
            ("template", self.template_hook),
        ):
            registration_s = self._registration_timeout(hook, origin)
            floor_s = self.internal_default_s + _MARGIN_S
            self.assertGreaterEqual(
                registration_s,
                floor_s,
                "%s registration timeout (%ss) < hook-internal default "
                "(%ss) + %ss margin: the harness would kill the hook "
                "BEFORE the hook's own codex subprocess cap fires, turning "
                "every slow verdict into an undiagnosable hook kill instead "
                "of a case-F TIMEOUT" % (
                    origin,
                    registration_s,
                    self.internal_default_s,
                    _MARGIN_S,
                ),
            )

    # -- invariant 3: statusMessage present in BOTH registrations ----------

    def test_status_message_present_in_both_registrations(self) -> None:
        for origin, hook in (
            ("kernel .claude/settings.json", self.kernel_hook),
            ("template settings.base.json", self.template_hook),
        ):
            status = hook.get("statusMessage")
            self.assertIsInstance(
                status,
                str,
                "pair-rail registration in %s has no 'statusMessage' — a "
                "180s+ canonical-edit stall must tell the operator the "
                "pair-rail review is running, not look like a hang "
                "(got %r)" % (origin, status),
            )
            self.assertTrue(
                status.strip(),
                "pair-rail registration statusMessage in %s is empty"
                % origin,
            )

    # -- invariant 4: ratified ABSOLUTE values (anti-downward-drift) -------

    def test_ratified_absolute_values(self) -> None:
        self.assertEqual(
            self.internal_default_s,
            _RATIFIED_INTERNAL_S,
            "hook-internal default is %ss but the ratified contract is %ss "
            "(PLAN-164 OQ1) — a change here must be a governed recalibration "
            "that edits this test in the same change (ADR-110-AMEND-1)"
            % (self.internal_default_s, _RATIFIED_INTERNAL_S),
        )
        fallbacks = _FALLBACK_RE.findall(
            _HOOK_SOURCE.read_text(encoding="utf-8")
        )
        self.assertEqual(
            fallbacks,
            [str(_RATIFIED_INTERNAL_S)] * 2,
            "check_pair_rail.py fallback/clamp-reset literals must BOTH be "
            "%d.0 (got %r) — a drifted fallback re-admits the broken value "
            "exactly on the parse-error/overflow path" % (
                _RATIFIED_INTERNAL_S, fallbacks,
            ),
        )
        for origin, hook in (
            ("kernel", self.kernel_hook),
            ("template", self.template_hook),
        ):
            self.assertEqual(
                self._registration_timeout(hook, origin),
                float(_RATIFIED_REGISTRATION_S),
                "%s registration timeout != ratified %ss (PLAN-164 OQ2) — "
                "recalibrate via a governed change that edits this test too"
                % (origin, _RATIFIED_REGISTRATION_S),
            )


if __name__ == "__main__":
    unittest.main()
