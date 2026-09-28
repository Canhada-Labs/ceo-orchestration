"""S218 / PLAN-128-FOLLOWUP — regression guard against the global subagent-model override.

Root cause it locks down: `CLAUDE_CODE_SUBAGENT_MODEL=haiku` was wired globally
(S206) into the dogfood settings, the adopter template, and `route.py`'s documented
SETTINGS_DELTA, and propagated by `install-accelerators.sh`. At the time (S218) the
Claude Code model-config docs said that env var OVERRIDES per-agent `model:`
frontmatter AND the per-invocation `model` param, so it silently downgraded EVERY
subagent — including governance VETO rites declared as opus (code-reviewer,
security-engineer) and adopters' deliberately-declared sonnet/opus agents — to Haiku.

Substrate change (Claude Code changelog, read 2026-09-22 on 2.1.280): since 2.1.251
`CLAUDE_CODE_SUBAGENT_MODEL` is only the DEFAULT subagent model (a definition's
`model:` and an explicit per-spawn model win over it), and since 2.1.257
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` carries the override role: when on, every
subagent runs on the subagent model (or the main model) and `model:` frontmatter and
per-spawn models are ignored. FORCE is the second carrier of the same flatten class
(ADR-144), so it is guarded here too.

NO test asserted the value, which is exactly why it shipped and ran unnoticed for
~11 sessions. These assertions:
  1. the dogfood + template settings set the env to "inherit" (normal resolution),
  2. the two are in sync (the existing parity test only diffs HOOK tuples, not env —
     Codex P1), and never re-introduce the global "haiku" value,
  3. route.py's SETTINGS_DELTA doctrine matches,
  4. the per-agent frontmatter tiering still exists (strong rites are not Haiku),
  5. no dogfood or template settings env, and no SETTINGS_DELTA, ever sets
     `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` (detector proven by a positive control),
  6. the installer never writes FORCE and warns at runtime when it is on in any
     env carrier it checks: the shell, user settings (under $CLAUDE_CONFIG_DIR when
     that is set, and under ~/.claude either way), and the app's project and local
     settings; an adopter's own FORCE value is left as it was (neither removed nor
     reset), the user and local settings files are never written, and a malformed
     carrier file is skipped, never fatal (behavioural, on a disposable app + HOME
     tree).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))

DOGFOOD_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
TEMPLATE_SETTINGS_DIR = REPO_ROOT / "templates" / "settings"
TEMPLATE_SETTINGS = TEMPLATE_SETTINGS_DIR / "settings.base.json"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
INSTALL_ACCEL = REPO_ROOT / "scripts" / "install-accelerators.sh"

_KEY = "CLAUDE_CODE_SUBAGENT_MODEL"
_FORCE_KEY = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"


def _env(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")).get("env", {})


def _settings_surfaces() -> List[Path]:
    """Every settings JSON whose env block reaches a session: the dogfood file plus
    every settings file the templates ship (glob, so a new profile is covered)."""
    return [DOGFOOD_SETTINGS] + sorted(TEMPLATE_SETTINGS_DIR.glob("*.json"))


def _force_violation(env: dict) -> Optional[str]:
    """The FORCE policy is "never set": ANY presence is a violation, whatever the
    value (a "0" today is one edit away from "1")."""
    if _FORCE_KEY in env:
        return f"{_FORCE_KEY}={env[_FORCE_KEY]!r}"
    return None


def _installer_merge_body() -> str:
    """The python heredoc install-accelerators.sh runs to merge the app settings."""
    src = INSTALL_ACCEL.read_text(encoding="utf-8")
    m = re.search(r"python3 - <<'PY'\n(.*?)\nPY\n", src, re.S)
    if m is None:
        raise AssertionError(
            f"{INSTALL_ACCEL}: settings-merge heredoc (python3 - <<'PY' ... PY) not "
            "found — update this locator together with the installer.")
    return m.group(1)


def _run_installer_merge(tmp: Path, shell_force: Optional[str] = None,
                         app_env: Optional[dict] = None,
                         user_env: Optional[dict] = None,
                         local_raw: Optional[str] = None,
                         config_dir_env: Optional[dict] = None) -> "subprocess.CompletedProcess":
    """Run the installer's merge step against a disposable app tree under `tmp`.
    HOME points into `tmp`, so the user-settings carrier is a planted file, never
    the real one. The framework settings are only READ; every write lands under
    `tmp`. `local_raw` is written verbatim as the app's settings.local.json (so a
    malformed file can be planted). `config_dir_env` plants a settings.json in a
    separate config home under `tmp` and points CLAUDE_CONFIG_DIR at it."""
    app = tmp / "app"
    home = tmp / "home"
    (app / ".claude").mkdir(parents=True)
    if app_env is not None:
        (app / ".claude" / "settings.json").write_text(
            json.dumps({"env": app_env}), encoding="utf-8")
    if local_raw is not None:
        (app / ".claude" / "settings.local.json").write_text(local_raw, encoding="utf-8")
    if user_env is not None:
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"env": user_env}), encoding="utf-8")
    child_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "FRAMEWORK": str(REPO_ROOT),
        "APP": str(app),
        "AUDIT_DIR": str(tmp / "audit"),
    }
    if shell_force is not None:
        child_env[_FORCE_KEY] = shell_force
    if config_dir_env is not None:
        config_home = tmp / "config-home"
        config_home.mkdir(parents=True)
        (config_home / "settings.json").write_text(
            json.dumps({"env": config_dir_env}), encoding="utf-8")
        child_env["CLAUDE_CONFIG_DIR"] = str(config_home)
    return subprocess.run(
        [sys.executable, "-"], input=_installer_merge_body(), env=child_env,
        capture_output=True, text=True, timeout=60,
    )


class SubagentModelOverrideRemoved(unittest.TestCase):
    def test_dogfood_settings_not_global_haiku(self):
        val = _env(DOGFOOD_SETTINGS).get(_KEY)
        self.assertEqual(
            val, "inherit",
            f"{DOGFOOD_SETTINGS} must set {_KEY}='inherit' (got {val!r}). A global "
            "'haiku' becomes the model of every subagent that declares none (and, "
            "before Claude Code 2.1.251, beat per-agent model: frontmatter too), "
            "downgrading governance rites — see PLAN-128-FOLLOWUP / S218.",
        )

    def test_template_settings_not_global_haiku(self):
        val = _env(TEMPLATE_SETTINGS).get(_KEY)
        self.assertEqual(
            val, "inherit",
            f"{TEMPLATE_SETTINGS} must set {_KEY}='inherit' (got {val!r}); adopters "
            "inherit this template and would silently downgrade every subagent that "
            "declares no model: (and, before Claude Code 2.1.251, every subagent).",
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
            "value.",
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
                         "install-accelerators.sh must NOT hardcode a global 'haiku' value.")
        # And it must not silently propagate whatever the framework env happens to be.
        self.assertNotIn('= fw_env["CLAUDE_CODE_SUBAGENT_MODEL"]', src,
                         "install-accelerators.sh must NOT propagate the framework's "
                         "subagent-model value into the adopter env.")

    # ---- CLAUDE_CODE_SUBAGENT_MODEL_FORCE (Claude Code 2.1.257+) -----------------

    def test_force_detector_positive_control(self):
        # The detector the settings guard relies on must FIRE on a planted value,
        # through the same file reader, or the guard below could be green by vacuum.
        self.assertIsNone(_force_violation({}))
        self.assertIsNone(_force_violation({_KEY: "inherit"}))
        for planted in ("1", "true", "0", ""):
            self.assertIsNotNone(_force_violation({_KEY: "inherit", _FORCE_KEY: planted}),
                                 f"detector missed a planted {_FORCE_KEY}={planted!r}")
        with tempfile.TemporaryDirectory() as d:
            planted_file = Path(d) / "settings.json"
            planted_file.write_text(
                json.dumps({"env": {_KEY: "inherit", _FORCE_KEY: "1"}}), encoding="utf-8")
            self.assertIsNotNone(_force_violation(_env(planted_file)))

    def test_force_never_set_in_dogfood_or_template_env(self):
        surfaces = _settings_surfaces()
        # Non-vacuity: the glob must still see the two files the other tests pin.
        self.assertIn(DOGFOOD_SETTINGS, surfaces)
        self.assertIn(TEMPLATE_SETTINGS, surfaces)
        for path in surfaces:
            hit = _force_violation(_env(path))
            self.assertIsNone(
                hit,
                f"{path} env sets {hit}. FORCE makes EVERY subagent ignore its model: "
                "frontmatter and per-spawn model (VETO rites below the floor with a "
                "cheap subagent model; tiering flattened upward with 'inherit').",
            )

    def test_route_settings_delta_never_sets_force(self):
        import route  # noqa: E402
        self.assertIsNone(_force_violation(route.SETTINGS_DELTA.get("env", {})),
                          "route.py SETTINGS_DELTA must never document FORCE.")

    def test_installer_warns_on_force_and_never_writes_it(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            # Negative control first: nothing set => no warning, so the warning
            # asserted below is conditional, not unconditional noise.
            quiet = _run_installer_merge(tmp / "quiet")
            self.assertEqual(quiet.returncode, 0, quiet.stderr)
            self.assertNotIn(_FORCE_KEY, quiet.stderr)
            # Claude Code's env boolean parser treats "0" as off: no warning either.
            off = _run_installer_merge(tmp / "off", shell_force="0")
            self.assertEqual(off.returncode, 0, off.stderr)
            self.assertNotIn("WARNING", off.stderr)

            shell = _run_installer_merge(tmp / "shell", shell_force="1")
            self.assertEqual(shell.returncode, 0, shell.stderr)
            self.assertIn("WARNING", shell.stderr)
            self.assertIn(_FORCE_KEY, shell.stderr)
            merged = _env(tmp / "shell" / "app" / ".claude" / "settings.json")
            self.assertEqual(merged.get(_KEY), "inherit")
            self.assertNotIn(_FORCE_KEY, merged,
                             "the installer must never write FORCE into the app env.")

            app = _run_installer_merge(tmp / "app-env", app_env={_FORCE_KEY: "true"})
            self.assertEqual(app.returncode, 0, app.stderr)
            self.assertIn("WARNING", app.stderr)
            app_file = tmp / "app-env" / "app" / ".claude" / "settings.json"
            self.assertIn(str(app_file) + " env", app.stderr)
            # "This installer does not change it": the merge rewrites the app
            # file (the audit dir proves the write happened) and the adopter's
            # own FORCE value survives it byte for byte, neither removed nor reset.
            merged_app = _env(app_file)
            self.assertEqual(merged_app.get("CEO_AUDIT_LOG_DIR"), str(tmp / "app-env" / "audit"))
            self.assertEqual(merged_app.get(_FORCE_KEY), "true",
                             "the installer must keep the adopter's own FORCE value as it was.")

            # User settings: the operator-scope carrier (HOME is the planted tree).
            user_raw = json.dumps({"env": {_FORCE_KEY: " Yes "}})
            user = _run_installer_merge(tmp / "user-env", user_env={_FORCE_KEY: " Yes "})
            self.assertEqual(user.returncode, 0, user.stderr)
            user_file = tmp / "user-env" / "home" / ".claude" / "settings.json"
            self.assertIn(str(user_file) + " env", user.stderr)
            self.assertNotIn(_FORCE_KEY, _env(tmp / "user-env" / "app" / ".claude" / "settings.json"))
            self.assertEqual(user_file.read_text(encoding="utf-8"), user_raw,
                             "the installer must never write the user settings file.")

            # Both config homes: with CLAUDE_CONFIG_DIR set (and clean there), a
            # FORCE planted only in ~/.claude/settings.json must still warn,
            # because a session started from another shell can resolve ~/.claude.
            both = _run_installer_merge(tmp / "both-homes", user_env={_FORCE_KEY: "1"},
                                        config_dir_env={_KEY: "inherit"})
            self.assertEqual(both.returncode, 0, both.stderr)
            self.assertIn(str(tmp / "both-homes" / "home" / ".claude" / "settings.json") + " env",
                          both.stderr)
            self.assertNotIn(str(tmp / "both-homes" / "config-home" / "settings.json") + " env",
                             both.stderr)

            # User settings under CLAUDE_CONFIG_DIR: Claude Code's config home moves
            # there when the variable is set, so a FORCE planted only there must warn.
            cfg = _run_installer_merge(tmp / "config-dir", config_dir_env={_FORCE_KEY: "1"})
            self.assertEqual(cfg.returncode, 0, cfg.stderr)
            self.assertIn(str(tmp / "config-dir" / "config-home" / "settings.json") + " env",
                          cfg.stderr)
            # Negative control: the variable set, the file there clean => no warning.
            cfg_quiet = _run_installer_merge(tmp / "config-dir-quiet",
                                             config_dir_env={_KEY: "inherit"})
            self.assertEqual(cfg_quiet.returncode, 0, cfg_quiet.stderr)
            self.assertNotIn("WARNING", cfg_quiet.stderr)

            local_raw = json.dumps({"env": {_FORCE_KEY: "on"}})
            local = _run_installer_merge(tmp / "local-env", local_raw=local_raw)
            self.assertEqual(local.returncode, 0, local.stderr)
            self.assertIn("settings.local.json env", local.stderr)
            local_file = tmp / "local-env" / "app" / ".claude" / "settings.local.json"
            self.assertEqual(local_file.read_text(encoding="utf-8"), local_raw,
                             "the installer must never write the local settings file.")
            self.assertNotIn(_FORCE_KEY,
                             _env(tmp / "local-env" / "app" / ".claude" / "settings.json"))

            # A malformed carrier file is skipped, never fatal (the check is advisory).
            broken = _run_installer_merge(tmp / "broken", local_raw="{not json")
            self.assertEqual(broken.returncode, 0, broken.stderr)
            self.assertNotIn("WARNING", broken.stderr)


if __name__ == "__main__":
    unittest.main()
