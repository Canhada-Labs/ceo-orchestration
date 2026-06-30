"""Template-vs-dogfood settings parity (Session 75 Codex Finding 2).

Closes Codex Finding 2: dogfood `.claude/settings.json` activated 6
hooks NOT mirrored in `templates/settings/settings.base.json`
(`check_tier_policy`, `check_arbitration_kernel`, `check_read_injection`,
`check_skill_reference_read`, `check_skill_bootstrap_post`,
`SubagentStop/check_fluency_nudge`) plus the plan-edit matcher had
drifted (`Edit` only vs dogfood `Edit|Write|MultiEdit`). Adopters
inheriting the template missed the broader governance surface.

Strategy:
- Parse both JSONs.
- Extract every (phase, matcher, hook_filename) tuple.
- Diff sets — assert template ⊇ dogfood (modulo allowlist for
  documented dogfood-only hooks if any are added later).
- Allowlist `DOGFOOD_ONLY_HOOKS` is currently empty; future entries
  must be justified inline.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

DOGFOOD_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
TEMPLATE_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.base.json"

_HOOK_RE = re.compile(r'_python-hook\.sh["\']?\s+([A-Za-z0-9_-]+\.py)')

# Hooks deliberately enabled only in the dogfood (this repo) and NOT
# shipped to adopters. MUST be empty by default — every entry needs a
# rationale comment.
DOGFOOD_ONLY_HOOKS: Set[Tuple[str, str, str]] = frozenset({
    # PLAN-102 v1.36.0 — autonomous-loop cost-envelope hook is dogfood-only
    # (the framework operates real swarms; adopters don't ship that surface
    # by default — Tier-C per ADR-125 §Tier C invariant).
    ("PreToolUse", "Bash", "check_cost_envelope.py"),
})


def _hook_ids(settings_path: Path) -> Set[Tuple[str, str, str]]:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    out: Set[Tuple[str, str, str]] = set()
    for phase, blocks in data.get("hooks", {}).items():
        for block in blocks:
            matcher = block.get("matcher", "*")
            for hook in block.get("hooks", []) or []:
                cmd = hook.get("command", "") or ""
                m = _HOOK_RE.search(cmd)
                if m:
                    out.add((phase, matcher, m.group(1)))
    return out


class TemplateDogfoodParityTest(TestEnvContext):
    def test_template_mirrors_dogfood(self) -> None:
        dogfood = _hook_ids(DOGFOOD_SETTINGS)
        template = _hook_ids(TEMPLATE_SETTINGS)
        missing_in_template = (dogfood - template) - DOGFOOD_ONLY_HOOKS
        self.assertFalse(
            missing_in_template,
            f"Template settings missing {len(missing_in_template)} hook(s) "
            f"that dogfood activates (Codex Finding 2 regression risk): "
            f"{sorted(missing_in_template)}\n"
            "Add them to templates/settings/settings.base.json or, if dogfood-only,"
            " add to DOGFOOD_ONLY_HOOKS allowlist with a rationale comment.",
        )

    def test_template_does_not_add_unknown_hooks(self) -> None:
        dogfood = _hook_ids(DOGFOOD_SETTINGS)
        template = _hook_ids(TEMPLATE_SETTINGS)
        extra = template - dogfood
        # Template-only hooks would mean adopters get something dogfood
        # doesn't run — counter-direction risk. Should be empty unless
        # a stack-overlay-only baseline adopter scenario exists.
        self.assertFalse(
            extra,
            f"Template has {len(extra)} hook(s) not in dogfood: {sorted(extra)}",
        )

    def test_plan_edit_matcher_covers_write_multiedit(self) -> None:
        """Session 75 Codex Finding 2: plan-edit matcher must also match
        Write|MultiEdit (not just Edit) per PLAN-019 P1-SEC-E."""
        for path in (DOGFOOD_SETTINGS, TEMPLATE_SETTINGS):
            data = json.loads(path.read_text(encoding="utf-8"))
            found = False
            for block in data["hooks"].get("PreToolUse", []):
                cmd = " ".join(h.get("command", "") for h in block.get("hooks", []))
                if "check_plan_edit" in cmd:
                    found = True
                    matcher = block.get("matcher", "")
                    self.assertIn("Edit", matcher)
                    self.assertIn("Write", matcher)
                    self.assertIn("MultiEdit", matcher)
            self.assertTrue(found, f"check_plan_edit missing from {path.name}")


if __name__ == "__main__":
    unittest.main()
