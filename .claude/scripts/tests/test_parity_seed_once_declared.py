"""PLAN-193 (S357) — every seed-once project-root template is DECLARED in the parity classifier.

Covers scripts/tests/_parity_classify.py (the classifier lives at repo-root
scripts/tests/, which is absent from pytest.ini testpaths — see the header of
test_parity_source_resolution.py for why its tests live here).

The class this closes. install.sh writes the project-root files CLAUDE.md,
MEMORY.md and .mcp.json from ONE list, `_FIXED_TEMPLATES_MAINTAINER`
(install_template, EXISTS->SKIP, maintainer ceremony only). upgrade.sh never
writes them: they are the adopter's after the seed. The parity e2e compares a
fresh install (route A) against an old install plus an upgrade (route B), so
for these files B keeps the OLD generation by design — and the classifier calls
that STALE, which is FATAL, unless an ACCEPTED entry declares the path.

The divergence is invisible while a template does not change, so a missing
declaration surfaces only years later, on the first release that edits the
template, as a red Smoke Install in the middle of a release train:
  1st occurrence (S332): `.claude/adr/README.md` (a sibling seed, declared then);
  2nd occurrence (S357): `.mcp.json`, when PLAN-193 emptied `mcpServers`.
This test moves the failure to the moment a seed row is ADDED: every
destination in `_FIXED_TEMPLATES_MAINTAINER` must be matched by an ACCEPTED
entry that applies to the maintainer ceremony.

Read-only on the live repo (install.sh and the classifier module); the parse
is fail-closed — a missing or empty block is a failure, never a free pass.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
CLASSIFIER = REPO / "scripts" / "tests" / "_parity_classify.py"
INSTALL_SH = REPO / "scripts" / "install.sh"

_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("_parity_classify", CLASSIFIER)
pc = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(pc)  # type: ignore[union-attr]

_BLOCK_RE = re.compile(r'^_FIXED_TEMPLATES_MAINTAINER="([^"]*)"', re.MULTILINE)


def seed_destinations(install_text: str) -> List[str]:
    """Destination halves of the `_FIXED_TEMPLATES_MAINTAINER` rows.

    Fail-closed: raises if the block is absent, empty, or a row is not
    `source|destination`.
    """
    found = _BLOCK_RE.findall(install_text)
    if len(found) != 1:
        raise AssertionError(
            "expected exactly one _FIXED_TEMPLATES_MAINTAINER block in "
            "install.sh, found %d" % len(found)
        )
    dests: List[str] = []
    for row in found[0].splitlines():
        row = row.strip()
        if not row:
            continue
        parts = row.split("|")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise AssertionError("malformed seed row %r" % row)
        dests.append(parts[1])
    if not dests:
        raise AssertionError("_FIXED_TEMPLATES_MAINTAINER has no rows")
    return dests


def undeclared(
    dests: Sequence[str],
    accepted: Sequence[Tuple[str, Optional[str], str]],
) -> List[str]:
    """Destinations no ACCEPTED entry covers in the maintainer ceremony."""
    missing: List[str] = []
    for dest in dests:
        covered = any(
            (modes is None or modes == "maintainer") and pc._matches(dest, pattern)
            for pattern, modes, _reason in accepted
        )
        if not covered:
            missing.append(dest)
    return missing


class TestSeedOnceTemplatesDeclared(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.dests = seed_destinations(INSTALL_SH.read_text(encoding="utf-8"))

    def test_seed_block_is_parsed(self) -> None:
        # Non-vacuity: an empty list would make the census below a free pass.
        self.assertIn("CLAUDE.md", self.dests)
        self.assertGreaterEqual(len(self.dests), 2)

    def test_every_seed_destination_is_declared_accepted(self) -> None:
        self.assertEqual(
            undeclared(self.dests, pc.ACCEPTED),
            [],
            "seed-once project-root template(s) with no ACCEPTED entry in "
            "scripts/tests/_parity_classify.py: the parity e2e goes FATAL "
            "[STALE] on the first release that edits the template. Declare "
            "each one, with its authority, for the maintainer ceremony.",
        )

    def test_census_detects_a_missing_declaration(self) -> None:
        # Negative control on the REAL list: drop every entry that covers one
        # seed destination and the census must name exactly that destination.
        target = self.dests[-1]
        pruned = [
            entry for entry in pc.ACCEPTED if not pc._matches(target, entry[0])
        ]
        self.assertLess(len(pruned), len(pc.ACCEPTED))
        self.assertEqual(undeclared([target], pruned), [target])

    def test_user_only_entry_does_not_count(self) -> None:
        # An entry scoped to the user ceremony does not cover a maintainer seed.
        fake = [(r"^CLAUDE\.md$", "user", "scoped to the wrong ceremony")]
        self.assertEqual(undeclared(["CLAUDE.md"], fake), ["CLAUDE.md"])

    def test_parse_is_fail_closed(self) -> None:
        with self.assertRaises(AssertionError):
            seed_destinations("#!/bin/bash\n")
        with self.assertRaises(AssertionError):
            seed_destinations('_FIXED_TEMPLATES_MAINTAINER="templates/x"\n')
        with self.assertRaises(AssertionError):
            seed_destinations('_FIXED_TEMPLATES_MAINTAINER=""\n')


if __name__ == "__main__":
    unittest.main()
