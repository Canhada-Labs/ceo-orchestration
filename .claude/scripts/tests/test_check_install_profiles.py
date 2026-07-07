#!/usr/bin/env python3
"""Tests for check-install-profiles.py (PLAN-153 item B4).

All fixture trees are built under ``tmp_path`` and the validator is driven
via ``--repo-root`` / ``--manifest``, so ``$HOME`` / ``$CLAUDE_PROJECT_DIR``
are never touched and no ``os.environ`` mutation happens anywhere
(env-hygiene gate). install.sh is never executed — the validator only
parses it statically, and these tests assert exactly that contract.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _SCRIPTS_DIR / "check-install-profiles.py"
_REPO_ROOT = _SCRIPTS_DIR.parent.parent


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_install_profiles", str(_SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


_INSTALL_SH = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# fixture install.sh — parsed statically, NEVER executed",
        'PROFILE="core,frontend"',
        "has_profile() { return 0; }",
        'if has_profile "core"; then true; fi',
        'if has_profile "frontend"; then true; fi',
        'if has_profile "fintech"; then echo dedicated; fi',
        "exit 7  # tripwire: executing this fixture would be a test bug",
        "",
    ]
)

_SETTINGS_BASE = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" audit_log.py',
                    },
                    {
                        "type": "command",
                        "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh"',
                    },
                ],
            }
        ]
    }
}


def _base_manifest() -> dict:
    return {
        "schema_version": 1,
        "default_profiles": ["core", "frontend"],
        "derivation": {
            "est_context_cost_rule": {
                "metric": "count of SKILL.md files under the profile's skill root",
                "low_max": 9,
                "med_max": 25,
                "else": "high",
            }
        },
        "hook_stacks": {
            "base": {
                "description": "fixture base stack",
                "settings_template": "templates/settings/settings.base.json",
                "selected_by": "always",
            }
        },
        "profiles": [
            {
                "name": "core",
                "description": "fixture core",
                "skill_globs": [".claude/skills/core/*/SKILL.md"],
                "hook_stacks": ["base"],
                "stability": "stable",
                "est_context_cost": "low",
            },
            {
                "name": "frontend",
                "description": "fixture frontend",
                "skill_globs": [".claude/skills/frontend/*/SKILL.md"],
                "hook_stacks": ["base"],
                "stability": "stable",
                "est_context_cost": "low",
            },
            {
                "name": "fintech",
                "description": "fixture fintech (dedicated block)",
                "skill_globs": [".claude/skills/domains/fintech/**/*"],
                "hook_stacks": ["base"],
                "stability": "stable",
                "est_context_cost": "low",
            },
            {
                "name": "alpha",
                "description": "fixture generic domain",
                "skill_globs": [".claude/skills/domains/alpha/**/*"],
                "hook_stacks": ["base"],
                "stability": "experimental",
                "est_context_cost": "low",
            },
        ],
        "consumption": {"status": "not_yet_consumed"},
    }


def _mk_repo(tmp_path: Path, manifest: dict = None, install_sh: str = None) -> Path:
    root = tmp_path / "repo"
    _write(root, "scripts/install.sh", install_sh if install_sh is not None else _INSTALL_SH)
    _write(root, ".claude/skills/core/skill-a/SKILL.md", "# a\n")
    _write(root, ".claude/skills/frontend/skill-b/SKILL.md", "# b\n")
    _write(root, ".claude/skills/domains/fintech/skills/skill-c/SKILL.md", "# c\n")
    _write(root, ".claude/skills/domains/alpha/pitfalls.yaml", "pitfalls: []\n")
    _write(
        root,
        "templates/settings/settings.base.json",
        json.dumps(_SETTINGS_BASE, indent=2) + "\n",
    )
    _write(root, ".claude/hooks/audit_log.py", "# hook\n")
    _write(root, ".claude/hooks/guard.sh", "# hook\n")
    _write(root, ".claude/hooks/_python-hook.sh", "# shim\n")
    doc = manifest if manifest is not None else _base_manifest()
    _write(root, "scripts/profiles/profiles.json", json.dumps(doc, indent=2) + "\n")
    return root


def _run(root: Path, **kw) -> int:
    argv = ["--repo-root", str(root)]
    if "manifest" in kw:
        argv += ["--manifest", str(kw["manifest"])]
    if kw.get("as_json"):
        argv += ["--json"]
    return MOD.main(argv)


# ---------------------------------------------------------------------------
# happy path + exit-code contract
# ---------------------------------------------------------------------------
def test_happy_path_rc0(tmp_path: Path, capsys) -> None:
    root = _mk_repo(tmp_path)
    assert _run(root) == 0
    assert "OK" in capsys.readouterr().out


def test_missing_manifest_rc2(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    (root / "scripts/profiles/profiles.json").unlink()
    assert _run(root) == 2


def test_missing_install_sh_rc2(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    (root / "scripts/install.sh").unlink()
    assert _run(root) == 2


def test_malformed_json_rc1(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    _write(root, "scripts/profiles/profiles.json", "{ not json")
    findings, infra = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert infra == []
    assert any(f.startswith("PARSE:") for f in findings)
    assert _run(root) == 1


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
def test_bad_stability_enum_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][3]["stability"] = "beta"
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("stability" in f and f.startswith("SCHEMA:") for f in findings)


def test_missing_profile_field_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    del doc["profiles"][0]["est_context_cost"]
    root = _mk_repo(tmp_path, manifest=doc)
    assert _run(root) == 1


def test_unknown_top_level_key_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["surprise"] = True
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("unknown top-level key 'surprise'" in f for f in findings)


def test_duplicate_profile_names_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"].append(copy.deepcopy(doc["profiles"][3]))
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("duplicate profile names" in f for f in findings)


# ---------------------------------------------------------------------------
# skill globs
# ---------------------------------------------------------------------------
def test_glob_matching_nothing_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][0]["skill_globs"] = [".claude/skills/core/*/NOPE.md"]
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(f.startswith("GLOB:") and "matches nothing" in f for f in findings)


def test_absolute_glob_rejected(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][0]["skill_globs"] = ["/etc/*"]
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("repo-relative" in f for f in findings)


# ---------------------------------------------------------------------------
# hook stacks
# ---------------------------------------------------------------------------
def test_referenced_hook_missing_rc1(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    (root / ".claude/hooks/audit_log.py").unlink()
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        f.startswith("HOOKS:") and ".claude/hooks/audit_log.py" in f for f in findings
    )


def test_profile_missing_base_stack_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["hook_stacks"]["other"] = {
        "description": "x",
        "settings_template": "templates/settings/settings.base.json",
        "selected_by": "never",
    }
    doc["profiles"][0]["hook_stacks"] = ["other"]
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("must include hook stack 'base'" in f for f in findings)


def test_undefined_stack_reference_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][0]["hook_stacks"] = ["base", "ghost"]
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("undefined hook stack 'ghost'" in f for f in findings)


def test_disk_stack_template_without_entry_is_drift(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    _write(root, "templates/settings/settings.stack.node.json", "{}\n")
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "DRIFT: settings template on disk has no hook_stacks entry" in f
        for f in findings
    )


# ---------------------------------------------------------------------------
# install.sh cross-check (static parse — never executed)
# ---------------------------------------------------------------------------
def test_default_profile_drift_rc1(tmp_path: Path) -> None:
    sh = _INSTALL_SH.replace('PROFILE="core,frontend"', 'PROFILE="core"')
    root = _mk_repo(tmp_path, install_sh=sh)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any("DRIFT: default_profiles" in f for f in findings)


def test_domain_on_disk_missing_from_manifest_rc1(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    _write(root, ".claude/skills/domains/newdomain/pitfalls.yaml", "x: 1\n")
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "domain dir on disk has no manifest profile: newdomain" in f for f in findings
    )


def test_phantom_manifest_domain_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"].append(
        {
            "name": "phantom",
            "description": "not on disk",
            "skill_globs": [".claude/skills/core/*/SKILL.md"],
            "hook_stacks": ["base"],
            "stability": "experimental",
            "est_context_cost": "low",
        }
    )
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "manifest profile 'phantom' has no domain dir on disk" in f for f in findings
    )


def test_stability_drift_dedicated_domain_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][2]["stability"] = "experimental"  # fintech has dedicated block
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "profile 'fintech' stability 'experimental' != derived 'stable'" in f
        for f in findings
    )


def test_stability_drift_generic_domain_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][3]["stability"] = "stable"  # alpha has NO dedicated block
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "profile 'alpha' stability 'stable' != derived 'experimental'" in f
        for f in findings
    )


def test_est_context_cost_drift_rc1(tmp_path: Path) -> None:
    doc = _base_manifest()
    doc["profiles"][0]["est_context_cost"] = "high"  # core fixture has 1 SKILL.md
    root = _mk_repo(tmp_path, manifest=doc)
    findings, _ = MOD.run_checks(root, root / "scripts/profiles/profiles.json")
    assert any(
        "profile 'core' est_context_cost 'high' != derived 'low'" in f
        for f in findings
    )


def test_install_sh_is_never_executed(tmp_path: Path) -> None:
    # A fixture install.sh whose EXECUTION would create a tripwire file;
    # static parsing must leave no trace.
    tripwire = tmp_path / "executed.flag"
    sh = _INSTALL_SH + '\ntouch "%s"\n' % tripwire
    root = _mk_repo(tmp_path, install_sh=sh)
    assert _run(root) == 0
    assert not tripwire.exists()


# ---------------------------------------------------------------------------
# --json output
# ---------------------------------------------------------------------------
def test_json_output_shape(tmp_path: Path, capsys) -> None:
    doc = _base_manifest()
    doc["profiles"][0]["est_context_cost"] = "high"
    root = _mk_repo(tmp_path, manifest=doc)
    rc = _run(root, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "findings"
    assert payload["exit_code"] == 1
    assert payload["findings"]
    assert payload["infra_errors"] == []


# ---------------------------------------------------------------------------
# the real repo: profiles.json must mirror the live install.sh truth
# ---------------------------------------------------------------------------
def test_real_repo_manifest_is_green() -> None:
    findings, infra = MOD.run_checks(
        _REPO_ROOT, _REPO_ROOT / "scripts/profiles/profiles.json"
    )
    assert infra == []
    assert findings == []
