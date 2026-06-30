"""Advisory lifecycle test for SIEM rule fixture pairs (PLAN-087 Wave E.1).

Per F-A-TDE-T-XXXX (P2, Codex CONFIRM/coarse): SIEM rules emitted via
``audit-query.py`` subcommands SHOULD have paired positive (``.pos.jsonl``)
and negative (``.neg.jsonl``) test fixtures under
``.claude/scripts/tests/fixtures/siem/<rule-slug>/``. This test walks
that directory and asserts each rule slug has BOTH directions.

ADVISORY-ONLY contract (PLAN-087 Wave E AC-E-4, SKILL §Detection-as-Code):

* This test MUST NOT gate CI. Skip / xfail when fixtures absent.
* It MUST NOT be elevated to fail-CLOSED without explicit pre-deploy
  FPR measurement on historical data (SKILL §Detection-as-Code budget).
* Future PLAN-091+ follow-on (row "SIEM rule fixture-pair seed corpus")
  may elevate after fixture corpus matures + pre-deploy FPR sample.

Stdlib-only per ADR-002.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, List, Set

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES_DIR = (
    _REPO_ROOT / ".claude" / "scripts" / "tests" / "fixtures" / "siem"
)


def _enumerate_rule_slugs(root: Path) -> Dict[str, Set[str]]:
    """Walk ``root`` and group fixture files by rule-slug subdirectory.

    Returns ``{rule_slug: {direction, ...}}`` where direction is
    ``"positive"`` or ``"negative"`` per filename suffix
    (``.pos.jsonl`` / ``.neg.jsonl``). Unknown suffixes ignored.
    """
    out: Dict[str, Set[str]] = {}
    if not root.exists() or not root.is_dir():
        return out
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        slug = child.name
        if slug.startswith("."):
            continue
        directions: Set[str] = set()
        for f in child.iterdir():
            if not f.is_file():
                continue
            name = f.name.lower()
            if name.endswith(".pos.jsonl"):
                directions.add("positive")
            elif name.endswith(".neg.jsonl"):
                directions.add("negative")
        if directions:
            out[slug] = directions
    return out


class SiemRuleFixturePairTest(unittest.TestCase):
    """Advisory: every SIEM rule slug should have positive + negative."""

    def test_fixture_dir_exists(self) -> None:
        """Directory existence is part of the lifecycle contract."""
        self.assertTrue(
            _FIXTURES_DIR.exists() and _FIXTURES_DIR.is_dir(),
            f"Advisory: expected fixtures dir at {_FIXTURES_DIR}",
        )

    def test_each_rule_slug_has_both_directions(self) -> None:
        """Each rule slug should ship .pos.jsonl AND .neg.jsonl pair."""
        if not _FIXTURES_DIR.exists():
            self.skipTest(
                "ADVISORY (PLAN-087 E.1): fixtures dir absent; "
                "seed corpus tracked in PLAN-091+ TDE backlog row "
                "'SIEM rule fixture-pair seed corpus'."
            )
        slugs = _enumerate_rule_slugs(_FIXTURES_DIR)
        if not slugs:
            self.skipTest(
                "ADVISORY (PLAN-087 E.1): no rule slugs populated yet "
                "under fixtures/siem/. Future PLAN-091+ row covers "
                "the seed corpus for the 5 ATLAS-mapped audit actions "
                "(prompt_injection_detected / secret_leak_detected / "
                "pii_redacted_outgoing / live_adapter_blocked / "
                "codex_egress_redacted)."
            )
        missing: List[str] = []
        for slug, directions in sorted(slugs.items()):
            if "positive" not in directions:
                missing.append(f"{slug}: missing .pos.jsonl")
            if "negative" not in directions:
                missing.append(f"{slug}: missing .neg.jsonl")
        if missing:
            # Advisory contract — emit list but DO NOT fail. Future
            # PLAN-091+ row converts to assertEqual once corpus stable.
            print(
                "ADVISORY (PLAN-087 E.1): "
                + str(len(missing))
                + " fixture-pair gaps:"
            )
            for m in missing:
                print("  - " + m)
        # Intentional: PASS at v1.21.0 even with gaps (advisory contract).
        # Conversion to assertEqual(missing, []) deferred to PLAN-091+.
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
