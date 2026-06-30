"""S218 / PLAN-128-FOLLOWUP — regression guard against the global subagent-model override.

Root cause it locks down: `CLAUDE_CODE_SUBAGENT_MODEL=haiku` was wired globally
(S206) into the dogfood settings, the adopter template, and `route.py`'s documented
SETTINGS_DELTA, and propagated by `install-accelerators.sh`. Per the Claude Code
model-config docs that env var OVERRIDES per-agent `model:` frontmatter AND the
per-invocation `model` param, so it silently downgraded EVERY subagent — including
governance VETO rites declared as opus (code-reviewer, security-engineer) and
adopters' deliberately-declared sonnet/opus agents — to Haiku.

NO test asserted the value, which is exactly why it shipped and ran unnoticed for
~11 sessions. These assertions:
  1. the dogfood + template settings set the env to "inherit" (normal resolution),
  2. the two are in sync (the existing parity test only diffs HOOK tuples, not env —
     Codex P1), and never re-introduce the global "haiku" override,
  3. route.py's SETTINGS_DELTA doctrine matches,
  4. the per-agent frontmatter tiering still exists (strong rites are not Haiku).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))

DOGFOOD_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
TEMPLATE_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.base.json"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
INSTALL_ACCEL = REPO_ROOT / "scripts" / "install-accelerators.sh"

_KEY = "CLAUDE_CODE_SUBAGENT_MODEL"


def _env(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")).get("env", {})


class SubagentModelOverrideRemoved(unittest.TestCase):
    def test_dogfood_settings_not_global_haiku(self):
        val = _env(DOGFOOD_SETTINGS).get(_KEY)
        self.assertEqual(
            val, "inherit",
            f"{DOGFOOD_SETTINGS} must set {_KEY}='inherit' (got {val!r}). A global "
            "'haiku' override beats per-agent model: frontmatter and downgrades "
            "governance rites — see PLAN-128-FOLLOWUP / S218.",
        )

    def test_template_settings_not_global_haiku(self):
        val = _env(TEMPLATE_SETTINGS).get(_KEY)
        self.assertEqual(
            val, "inherit",
            f"{TEMPLATE_SETTINGS} must set {_KEY}='inherit' (got {val!r}); adopters "
            "inherit this template and would silently downgrade every subagent.",
        )

    def test_dogfood_and_template_env_parity(self):
        # Codex P1: the existing parity test diffs hook tuples only, NOT env values —
        # so the two settings files could drift on this key undetected.
        self.assertEqual(
            _env(DOGFOOD_SETTINGS).get(_KEY), _env(TEMPLATE_SETTINGS).get(_KEY),
            f"dogfood and template settings disagree on {_KEY}.",
        )

    def test_route_settings_delta_doctrine(self):
        import route  # noqa: E402
        self.assertEqual(
            route.SETTINGS_DELTA["env"][_KEY], "inherit",
            "route.py SETTINGS_DELTA must document 'inherit', not a global 'haiku' "
            "override.",
        )

    def test_strong_rites_are_not_haiku(self):
        # The tiering the override was masking: code-review + security VETO rites are
        # declared on a strong model in their frontmatter. If a future change flattens
        # them (e.g. re-introduces a global override or edits the frontmatter), catch it.
        for name in ("code-reviewer", "security-engineer"):
            md = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
            model_line = next(
                (ln for ln in md.splitlines() if ln.strip().startswith("model:")), ""
            )
            # ADR-149 (PLAN-134 W0): floor tier = opus-class OR fable-class.
            # The guard's intent is unchanged — a VETO rite silently flattened
            # to haiku/sonnet must still fail loudly.
            self.assertTrue(
                ("opus" in model_line) or ("fable" in model_line),
                f"{name}.md should declare a floor-tier model (got {model_line!r}).",
            )

    def test_installer_forces_inherit_not_haiku(self):
        # Codex (019ea473) finding 1: the installer is the other vector — a future
        # hardcoded re-introduction there could re-poison adopter repos while the
        # settings/route assertions above stay green. Guard the installer source.
        src = INSTALL_ACCEL.read_text(encoding="utf-8")
        self.assertIn('env["CLAUDE_CODE_SUBAGENT_MODEL"] = "inherit"', src,
                      "install-accelerators.sh must force the app env to 'inherit'.")
        self.assertNotIn('env["CLAUDE_CODE_SUBAGENT_MODEL"] = "haiku"', src,
                         "install-accelerators.sh must NOT hardcode a global 'haiku' override.")
        # And it must not silently propagate whatever the framework env happens to be.
        self.assertNotIn('= fw_env["CLAUDE_CODE_SUBAGENT_MODEL"]', src,
                         "install-accelerators.sh must NOT propagate the framework's "
                         "subagent-model value into the adopter env.")


if __name__ == "__main__":
    unittest.main()
