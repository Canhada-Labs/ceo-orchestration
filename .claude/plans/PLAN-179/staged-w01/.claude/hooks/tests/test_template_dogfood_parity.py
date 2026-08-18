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

PLAN-163 T3.3/T3.4 (ADR-183) extension — the two NEW event registrations
(`DirectoryAdded` -> check_directory_added.py, `Notification` ->
check_notification.py) are wired in the DOGFOOD settings immediately but
DEFERRED from the template until the T3.4 version-floor probe is recorded
(CEO decision S284; ADR-183 residual e). They are NOT dogfood-only forever,
so they do not belong in `DOGFOOD_ONLY_HOOKS`; instead their expected
placement is DERIVED from the artifacts (codex F7/grok F5 — never
re-hardcoded):

- the canonical entries come from `upgrade.sh --print-settings-baselines`
  (the normative T5.4 table);
- the gate state comes from the static `_T34_VERSION_FLOOR_PROBE_PASSED=`
  default in scripts/upgrade.sh (parsed, not executed — the env override
  must not leak into a parity verdict);
- gate OFF  -> dogfood carries them, template must NOT;
- gate ON   -> the template must carry them too (flipping the gate without
  updating the template reddens this suite — the coupling is the oracle).

The intentional `check_cost_envelope.py` dogfood-only exclusion is
preserved and asserted to stay the ONLY non-gated difference.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

DOGFOOD_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
TEMPLATE_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.base.json"
UPGRADE_SH = REPO_ROOT / "scripts" / "upgrade.sh"

# PLAN-152 governance-02: the original single regex only matched the
# canonical `_python-hook.sh <basename>.py` form, so a registration using
# a relative-path arg (the v1.0.0 check_pair_rail.py drift) or a raw
# `python3 ".../.claude/hooks/<hook>.py"` invocation (check_codex_filewrite)
# was INVISIBLE to the parity diff — the assertion was vacuous for exactly
# the hooks most likely to drift. Two forms are now parsed; both extract
# the hook basename.
#
# Form A/B — the shim, with the first arg either a bare basename or a
# (legacy/drifted) relative path:
_SHIM_HOOK_RE = re.compile(
    r'_python-hook\.sh["\']?\s+(?:[\w.$/{}"\'-]*/)?([A-Za-z0-9_-]+\.py)'
)
# Form C — raw interpreter invocation of a hooks-dir script:
_RAW_PY_HOOK_RE = re.compile(
    r'python3?[\d.]*\s+["\']?[\w.$/{}-]*/\.claude/hooks/([A-Za-z0-9_-]+\.py)'
)
_HOOK_RES = (_SHIM_HOOK_RE, _RAW_PY_HOOK_RE)

# Hooks deliberately enabled only in the dogfood (this repo) and NOT
# shipped to adopters. MUST be empty by default — every entry needs a
# rationale comment.
DOGFOOD_ONLY_HOOKS: Set[Tuple[str, str, str]] = frozenset({
    # PLAN-102 v1.36.0 — autonomous-loop cost-envelope hook is dogfood-only
    # (the framework operates real swarms; adopters don't ship that surface
    # by default — Tier-C per ADR-125 §Tier C invariant).
    ("PreToolUse", "Bash", "check_cost_envelope.py"),
})

# PLAN-163 T6.4 ratified count literals (dogfood 46->48; template STAYS 45
# per CEO decision S284 / ADR-183 residual e). These pins are the closeout
# contract; the RELATIONSHIP between the two files is asserted separately
# in fully-derived form (template + dogfood-only + gated == dogfood).
#
# PLAN-179 W1-b REBASELINE (48->49 / 45->46): the Constraint Pinning hook
# `check_compact_pinning.py` adds ONE SessionStart block (matcher "compact")
# to BOTH mirrors in the same change. Both literals move by +1 because the
# registration is adopter-facing, NOT dogfood-only: an adopter who inherits
# the hook FILE without the registration gets a dead Constraint Pinning
# floor while this repo stays green — exactly the Codex Finding 2 class this
# suite exists to catch. It is NOT a T3.4-gated registration either (no
# version-floor probe: SessionStart + matcher are long-standing substrate),
# so it must NOT enter DOGFOOD_ONLY_HOOKS nor the gated set. The derived
# relationship below is the real oracle and is unchanged: 49 == 46 + 1 + 2.
T64_DOGFOOD_REGISTRATIONS = 49
T64_TEMPLATE_REGISTRATIONS = 46

_BASELINES_CACHE: Optional[Dict] = None


def _t54_baselines() -> Dict:
    """The normative T5.4 table, derived FROM THE ARTIFACT (never hardcoded)."""
    global _BASELINES_CACHE
    if _BASELINES_CACHE is None:
        proc = subprocess.run(
            ["bash", str(UPGRADE_SH), "--print-settings-baselines"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            raise AssertionError(
                "upgrade.sh --print-settings-baselines rc=%s stderr=%s"
                % (proc.returncode, proc.stderr)
            )
        _BASELINES_CACHE = json.loads(proc.stdout)
    return _BASELINES_CACHE


def _t34_gate_on() -> bool:
    """Static T3.4 gate default, parsed from the upgrade.sh ARTIFACT.

    Deliberately NOT `_t34_new_event_registrations_enabled` semantics: the
    CEO_T34_NEW_EVENT_REGISTRATIONS env override is a migration test seam /
    operator escape hatch and must never flip a parity verdict.
    """
    text = UPGRADE_SH.read_text(encoding="utf-8")
    m = re.search(r"^_T34_VERSION_FLOOR_PROBE_PASSED=([01])\b",
                  text, re.MULTILINE)
    if not m:
        raise AssertionError(
            "T3.4 gate default (_T34_VERSION_FLOOR_PROBE_PASSED=) not found "
            "in scripts/upgrade.sh — the parity oracle derives from it"
        )
    return m.group(1) == "1"


def _gated_registration_ids() -> Set[Tuple[str, str, str]]:
    """(phase, matcher, filename) ids of the T3.4-gated new-event
    registrations, DERIVED from the T5.4 table."""
    out: Set[Tuple[str, str, str]] = set()
    for event, spec in _t54_baselines().get("registrations", {}).items():
        out.add((event, spec["entry"].get("matcher", "*"), spec["match"]))
    return out


def _hook_ids(settings_path: Path) -> Set[Tuple[str, str, str]]:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    out: Set[Tuple[str, str, str]] = set()
    for phase, blocks in data.get("hooks", {}).items():
        for block in blocks:
            matcher = block.get("matcher", "*")
            for hook in block.get("hooks", []) or []:
                cmd = hook.get("command", "") or ""
                for rx in _HOOK_RES:
                    m = rx.search(cmd)
                    if m:
                        out.add((phase, matcher, m.group(1)))
                        break
    return out


def _registration_count(settings_path: Path) -> int:
    """Registrations = entry blocks across all event keys (the CLAUDE.md
    'event registrations' counting rule — includes non-shim blocks like the
    PostToolUse echo reminder)."""
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return sum(len(blocks) for blocks in data.get("hooks", {}).values())


class TemplateDogfoodParityTest(TestEnvContext):
    def test_template_mirrors_dogfood(self) -> None:
        dogfood = _hook_ids(DOGFOOD_SETTINGS)
        template = _hook_ids(TEMPLATE_SETTINGS)
        missing_in_template = (dogfood - template) - DOGFOOD_ONLY_HOOKS
        if not _t34_gate_on():
            # PLAN-163 T3.4 (ADR-183 residual e): the gated new-event
            # registrations are dogfood-now / template-later — excluded from
            # the mirror assertion ONLY while the version-floor gate is OFF.
            missing_in_template -= _gated_registration_ids()
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


class T3NewEventRegistrationParityTest(TestEnvContext):
    """PLAN-163 T3.3/T3.4 (ADR-183) — DirectoryAdded/Notification parity.

    Every expectation is DERIVED from the artifacts: the canonical entries
    from `upgrade.sh --print-settings-baselines`, the gate state from the
    static upgrade.sh default, the placement from the settings files.
    """

    def test_dogfood_carries_canonical_t54_entries(self) -> None:
        """Dogfood registers BOTH new events with the entry object
        byte-equal to the normative T5.4 table entry."""
        data = json.loads(DOGFOOD_SETTINGS.read_text(encoding="utf-8"))
        regs = _t54_baselines()["registrations"]
        self.assertTrue(regs, "T5.4 table has no registrations — artifact broken")
        for event, spec in regs.items():
            blocks = data.get("hooks", {}).get(event)
            self.assertIsInstance(
                blocks, list,
                f"dogfood settings.json missing hooks.{event} (T3 wiring)",
            )
            self.assertIn(
                spec["entry"], blocks,
                f"dogfood hooks.{event} does not contain the canonical T5.4 "
                f"entry byte-equal (drift between settings.json and the "
                f"upgrade.sh migration table)",
            )

    def test_template_gate_coupling(self) -> None:
        """Gate OFF -> template must NOT register the new events (residual e,
        45 registrations). Gate ON -> template MUST carry the canonical
        entries (flipping the gate without updating the template reddens)."""
        data = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        regs = _t54_baselines()["registrations"]
        gate_on = _t34_gate_on()
        for event, spec in regs.items():
            blocks = data.get("hooks", {}).get(event)
            if gate_on:
                self.assertIsInstance(
                    blocks, list,
                    f"T3.4 gate is ON but the template does not register "
                    f"hooks.{event} — update settings.base.json in the same "
                    f"change that flips the gate (ADR-183 residual e)",
                )
                self.assertIn(spec["entry"], blocks)
            else:
                self.assertIsNone(
                    blocks,
                    f"T3.4 gate is OFF (version-floor probe pending) but the "
                    f"template registers hooks.{event} — CEO decision S284 / "
                    f"ADR-183 residual e keeps the template at "
                    f"{T64_TEMPLATE_REGISTRATIONS} registrations until the "
                    f"probe is recorded",
                )

    def test_registration_counts(self) -> None:
        """T6.4 count pins + the fully-derived relationship between them."""
        dogfood = _registration_count(DOGFOOD_SETTINGS)
        template = _registration_count(TEMPLATE_SETTINGS)
        gated = 0 if _t34_gate_on() else len(_t54_baselines()["registrations"])
        # Derived relationship: every dogfood block is either mirrored in the
        # template, an allowlisted dogfood-only block, or a T3.4-gated block
        # (while the gate is OFF).
        self.assertEqual(
            dogfood, template + len(DOGFOOD_ONLY_HOOKS) + gated,
            "registration-count relationship broken: dogfood != template + "
            "dogfood-only + gated-while-off (an undocumented one-sided "
            "registration crept in)",
        )
        # T6.4 ratified pins (closeout contract; CLAUDE.md triple).
        self.assertEqual(dogfood, T64_DOGFOOD_REGISTRATIONS)
        self.assertEqual(template, T64_TEMPLATE_REGISTRATIONS)

    def test_cost_envelope_exclusion_is_the_only_ungated_difference(self) -> None:
        """The intentional check_cost_envelope.py exclusion is preserved and
        remains the ONLY dogfood-only shim hook besides the gated pair."""
        dogfood = _hook_ids(DOGFOOD_SETTINGS)
        template = _hook_ids(TEMPLATE_SETTINGS)
        ungated_diff = (dogfood - template) - _gated_registration_ids()
        self.assertEqual(
            ungated_diff, set(DOGFOOD_ONLY_HOOKS),
            "the non-gated dogfood-minus-template difference must be exactly "
            "the documented DOGFOOD_ONLY_HOOKS allowlist "
            "(check_cost_envelope.py)",
        )


class SessionDefaultPinTest(TestEnvContext):
    """PLAN-163 T1.1 (ADR-181 §Contingency) — the explicit session-default
    pin must ship in BOTH mirrors and stay inside the allowlist.

    CC 2.1.220 honors the top-level settings key ``model`` (string; zod
    ``E.string().optional().describe("Override the default model used by
    Claude Code")``; 2.1.220 binary offset 226819212, sha256 8addc857...).
    Pinning it forecloses the silent session-default flip to the sonnet-5
    tier-default that appending claude-sonnet-5 to availableModels would
    otherwise unmask (enforceAvailableModels stops redirecting once the tier
    default is an allowed model). The pinned value MUST remain a member of
    availableModels or enforceAvailableModels rejects it.
    """

    EXPECTED_PIN = "claude-opus-5"

    def test_dogfood_pins_session_default(self) -> None:
        data = json.loads(DOGFOOD_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(
            data.get("model"), self.EXPECTED_PIN,
            "dogfood .claude/settings.json must pin top-level "
            "'model' to claude-opus-5 (ADR-181 T1.1 contingency)",
        )

    def test_template_pins_session_default(self) -> None:
        data = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(
            data.get("model"), self.EXPECTED_PIN,
            "template settings.base.json must pin top-level "
            "'model' to claude-opus-5 (adopters inherit the pin)",
        )

    def test_pin_is_member_of_available_models_in_both_mirrors(self) -> None:
        for path in (DOGFOOD_SETTINGS, TEMPLATE_SETTINGS):
            data = json.loads(path.read_text(encoding="utf-8"))
            pin = data.get("model")
            available = data.get("availableModels")
            self.assertIsInstance(
                available, list,
                f"{path.name}: availableModels must be a list",
            )
            self.assertIn(
                pin, available,
                f"{path.name}: session-default pin '{pin}' is NOT in "
                "availableModels — enforceAvailableModels would reject it. "
                "Update the pin and the allowlist together.",
            )

    def test_both_mirrors_agree_on_the_pin(self) -> None:
        dogfood = json.loads(DOGFOOD_SETTINGS.read_text(encoding="utf-8"))
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(
            dogfood.get("model"), template.get("model"),
            "session-default pin drifted between dogfood and template "
            "(the two mirrors must carry an identical 'model' pin)",
        )


class UserTemplateSessionDefaultPinTest(TestEnvContext):
    """PLAN-163 T1.1 / FXe — the ADVISORY user-ceremony template must ALSO
    pin the session default.

    `install --ceremony user` copies templates/settings/settings.user.json
    verbatim to .claude/settings.json (base-only path) and, on the stack
    path, the jq reducer starts from that file as ``$base`` (top-level keys
    survive). Without a ``model`` pin a fresh user install inherits the CC
    2.1.220 sonnet-5 tier-default — the same silent-flip SessionDefaultPinTest
    closes for the maintainer/base mirror.

    Distinct from SessionDefaultPinTest by design: the user profile is
    advisory, so the pin must NOT be accompanied by availableModels /
    enforceAvailableModels. Asserting their ABSENCE is the guard against a
    maintainer 'helpfully' turning the advisory path into an enforcing one
    (which would change the profile's nature).
    """

    EXPECTED_PIN = "claude-opus-5"
    USER_TEMPLATE = REPO_ROOT / "templates" / "settings" / "settings.user.json"

    def test_user_template_pins_session_default(self) -> None:
        data = json.loads(self.USER_TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(
            data.get("model"), self.EXPECTED_PIN,
            "templates/settings/settings.user.json must pin top-level 'model' "
            "to claude-opus-5 so a fresh `install --ceremony user` does not "
            "inherit the CC 2.1.220 sonnet-5 tier-default (PLAN-163 FXe).",
        )

    def test_user_template_stays_advisory(self) -> None:
        """Advisory profile pins the default ONLY — the enforcing keys must be
        ABSENT, or the user path stops being advisory-only."""
        data = json.loads(self.USER_TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn(
            "enforceAvailableModels", data,
            "settings.user.json must NOT set enforceAvailableModels — the user "
            "ceremony is advisory by design (PLAN-163 FXe). The default pin is "
            "the minimum; adding enforcement changes the profile's nature.",
        )
        self.assertNotIn(
            "availableModels", data,
            "settings.user.json must NOT set availableModels — the advisory "
            "user path deliberately does not constrain the model set.",
        )

    def test_user_template_agrees_with_base_pin(self) -> None:
        """All adopter-facing mirrors carry the identical session-default pin;
        the user template must not drift from the base template."""
        user = json.loads(self.USER_TEMPLATE.read_text(encoding="utf-8"))
        base = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(
            user.get("model"), base.get("model"),
            "session-default pin drifted between the user template and the "
            "base template — the two adopter-facing mirrors must agree.",
        )


if __name__ == "__main__":
    unittest.main()
