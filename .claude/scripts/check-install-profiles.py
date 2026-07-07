#!/usr/bin/env python3
"""Validate scripts/profiles/profiles.json against disk + install.sh truth.

PLAN-153 item B4. profiles.json v1 is a DERIVED, CI-validated mirror of the
inline profile logic in ``scripts/install.sh`` — install.sh does NOT consume
it yet (the consumption flip is a recorded follow-up). This validator is the
drift tripwire: any divergence between the manifest, the disk skill trees,
the settings templates, or install.sh's own profile table turns CI red.

## Checks

1.  Manifest parses as JSON.
2.  Top-level + per-profile schema complete (required fields, enums,
    unique names, no unknown keys).
3.  Every ``skill_glob`` matches >= 1 path on disk under the repo root.
4.  Every profile ``hook_stacks`` entry is defined and includes ``base``
    (install.sh installs hooks unconditionally — section 5).
5.  Every hook-stack ``settings_template`` exists, parses, and every
    ``.claude/**.py|.sh`` hook it references exists on disk.
6.  Cross-check against install.sh's profile table (static parse — the
    script is never executed):
      a. default ``PROFILE="..."`` assignment == ``default_profiles``;
      b. domain dirs on disk == manifest domain profiles (both ways);
      c. ``stability`` matches the ratified rule (default profiles UNION
         domains with a dedicated ``has_profile "<name>"`` block);
      d. ``est_context_cost`` matches SKILL.md counts vs the thresholds
         recorded in the manifest's ``derivation`` block;
      e. hook-stack settings_templates <-> templates/settings/*.json
         bijection (a new stack template on disk without a manifest
         entry is drift, and vice versa).

## Usage

    python3 .claude/scripts/check-install-profiles.py
    python3 .claude/scripts/check-install-profiles.py --json
    python3 .claude/scripts/check-install-profiles.py --repo-root <path>

Exit codes:
    0 — manifest valid, no drift.
    1 — validation failure (schema, glob, hook, or drift finding).
    2 — infrastructure/usage error (repo root, manifest file, or
        install.sh missing/unreadable — the check could not run).

Stdlib-only (Python >= 3.9). Never executes install.sh.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

MANIFEST_REL = "scripts/profiles/profiles.json"
INSTALL_SH_REL = "scripts/install.sh"
DOMAINS_REL = ".claude/skills/domains"
SETTINGS_DIR_REL = "templates/settings"

SCHEMA_VERSION = 1
STABILITY_VALUES = ("stable", "experimental")
COST_VALUES = ("low", "med", "high")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

TOP_KEYS_REQUIRED = {
    "schema_version",
    "default_profiles",
    "derivation",
    "hook_stacks",
    "profiles",
    "consumption",
}
TOP_KEYS_ALLOWED = TOP_KEYS_REQUIRED | {"$comment"}
PROFILE_KEYS_REQUIRED = {
    "name",
    "description",
    "skill_globs",
    "hook_stacks",
    "stability",
    "est_context_cost",
}
PROFILE_KEYS_ALLOWED = PROFILE_KEYS_REQUIRED | {"notes"}
STACK_KEYS_REQUIRED = {"description", "settings_template", "selected_by"}

# install.sh static-parse anchors (never executed).
_DEFAULT_PROFILE_RE = re.compile(r'^PROFILE="([^"]+)"\s*$', re.MULTILINE)
_HAS_PROFILE_RE = re.compile(r'has_profile "([a-z0-9-]+)"')

# Hook references inside settings templates.
_PYHOOK_RE = re.compile(r'_python-hook\.sh"?\s+([A-Za-z0-9_.\-]+\.py)')
_CLAUDE_PATH_RE = re.compile(
    r"\$CLAUDE_PROJECT_DIR/(\.claude/[A-Za-z0-9_.\-/]+\.(?:py|sh))"
)


def _glob_prefix_dir(root: Path, pattern: str) -> Optional[Path]:
    """Directory prefix of ``pattern`` up to its first wildcard segment."""
    parts: List[str] = []
    for seg in pattern.split("/"):
        if any(ch in seg for ch in "*?["):
            break
        parts.append(seg)
    if not parts:
        return None
    return root / "/".join(parts)


def _iter_hook_commands(node: Any) -> List[str]:
    """Collect every ``command`` string in a settings ``hooks`` tree."""
    out: List[str] = []
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "command" and isinstance(val, str):
                out.append(val)
            else:
                out.extend(_iter_hook_commands(val))
    elif isinstance(node, list):
        for item in node:
            out.extend(_iter_hook_commands(item))
    return out


def _hook_refs_from_commands(commands: List[str]) -> Set[str]:
    refs: Set[str] = set()
    for cmd in commands:
        for name in _PYHOOK_RE.findall(cmd):
            refs.add(".claude/hooks/" + name)
        for rel in _CLAUDE_PATH_RE.findall(cmd):
            refs.add(rel)
    return refs


def _parse_install_sh(text: str) -> Tuple[Optional[List[str]], Set[str]]:
    """Return (default profile parts, dedicated has_profile names)."""
    default_parts: Optional[List[str]] = None
    match = _DEFAULT_PROFILE_RE.search(text)
    if match:
        default_parts = [p for p in match.group(1).split(",") if p]
    dedicated = set(_HAS_PROFILE_RE.findall(text)) - {"core", "frontend"}
    return default_parts, dedicated


def _check_top_schema(doc: Any, findings: List[str]) -> bool:
    """Validate top-level shape. Returns False if too broken to continue."""
    if not isinstance(doc, dict):
        findings.append("SCHEMA: manifest root must be a JSON object")
        return False
    missing = TOP_KEYS_REQUIRED - set(doc)
    unknown = set(doc) - TOP_KEYS_ALLOWED
    for key in sorted(missing):
        findings.append("SCHEMA: missing top-level key '%s'" % key)
    for key in sorted(unknown):
        findings.append("SCHEMA: unknown top-level key '%s'" % key)
    if doc.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            "SCHEMA: schema_version must be %d (got %r)"
            % (SCHEMA_VERSION, doc.get("schema_version"))
        )
    dp = doc.get("default_profiles")
    if not (isinstance(dp, list) and dp and all(isinstance(x, str) for x in dp)):
        findings.append("SCHEMA: default_profiles must be a non-empty list of strings")
    if not isinstance(doc.get("hook_stacks"), dict):
        findings.append("SCHEMA: hook_stacks must be an object")
        return False
    if not isinstance(doc.get("profiles"), list):
        findings.append("SCHEMA: profiles must be a list")
        return False
    return True


def _check_profile_schema(prof: Any, idx: int, findings: List[str]) -> bool:
    label = "profiles[%d]" % idx
    if not isinstance(prof, dict):
        findings.append("SCHEMA: %s must be an object" % label)
        return False
    ok = True
    for key in sorted(PROFILE_KEYS_REQUIRED - set(prof)):
        findings.append("SCHEMA: %s missing key '%s'" % (label, key))
        ok = False
    for key in sorted(set(prof) - PROFILE_KEYS_ALLOWED):
        findings.append("SCHEMA: %s unknown key '%s'" % (label, key))
        ok = False
    name = prof.get("name")
    if not (isinstance(name, str) and NAME_RE.match(name or "")):
        findings.append("SCHEMA: %s name %r invalid (want %s)" % (label, name, NAME_RE.pattern))
        ok = False
    if not (isinstance(prof.get("description"), str) and prof.get("description", "").strip()):
        findings.append("SCHEMA: %s description must be a non-empty string" % label)
        ok = False
    globs = prof.get("skill_globs")
    if not (isinstance(globs, list) and globs and all(isinstance(g, str) for g in globs)):
        findings.append("SCHEMA: %s skill_globs must be a non-empty list of strings" % label)
        ok = False
    stacks = prof.get("hook_stacks")
    if not (isinstance(stacks, list) and stacks and all(isinstance(s, str) for s in stacks)):
        findings.append("SCHEMA: %s hook_stacks must be a non-empty list of strings" % label)
        ok = False
    if prof.get("stability") not in STABILITY_VALUES:
        findings.append(
            "SCHEMA: %s stability %r not in %s" % (label, prof.get("stability"), list(STABILITY_VALUES))
        )
        ok = False
    if prof.get("est_context_cost") not in COST_VALUES:
        findings.append(
            "SCHEMA: %s est_context_cost %r not in %s"
            % (label, prof.get("est_context_cost"), list(COST_VALUES))
        )
        ok = False
    return ok


def _check_hook_stacks(root: Path, stacks: Dict[str, Any], findings: List[str]) -> None:
    for name in sorted(stacks):
        entry = stacks[name]
        label = "hook_stacks['%s']" % name
        if not isinstance(entry, dict):
            findings.append("SCHEMA: %s must be an object" % label)
            continue
        for key in sorted(STACK_KEYS_REQUIRED - set(entry)):
            findings.append("SCHEMA: %s missing key '%s'" % (label, key))
        tmpl = entry.get("settings_template")
        if not isinstance(tmpl, str):
            continue
        tmpl_path = root / tmpl
        if not tmpl_path.is_file():
            findings.append("HOOKS: %s settings_template not on disk: %s" % (label, tmpl))
            continue
        try:
            settings = json.loads(tmpl_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            findings.append("HOOKS: %s template unreadable/unparseable: %s" % (label, exc))
            continue
        commands = _iter_hook_commands(settings.get("hooks", {}))
        for ref in sorted(_hook_refs_from_commands(commands)):
            if not (root / ref).is_file():
                findings.append(
                    "HOOKS: %s references missing hook file: %s" % (label, ref)
                )
    # Bijection: manifest settings_templates <-> templates/settings/*.json on disk.
    settings_dir = root / SETTINGS_DIR_REL
    disk = set()
    if settings_dir.is_dir():
        disk = {
            "%s/%s" % (SETTINGS_DIR_REL, p.name)
            for p in settings_dir.glob("settings*.json")
        }
    declared = {
        e.get("settings_template")
        for e in stacks.values()
        if isinstance(e, dict) and isinstance(e.get("settings_template"), str)
    }
    for tmpl in sorted(disk - declared):
        findings.append("DRIFT: settings template on disk has no hook_stacks entry: %s" % tmpl)
    for tmpl in sorted(declared - disk):
        findings.append("DRIFT: hook_stacks declares template not on disk: %s" % tmpl)


def _check_skill_globs(root: Path, profiles: List[Dict[str, Any]], findings: List[str]) -> None:
    for prof in profiles:
        for pattern in prof.get("skill_globs", []):
            if not isinstance(pattern, str):
                continue
            if pattern.startswith("/") or ".." in pattern.split("/"):
                findings.append(
                    "GLOB: profile '%s' glob must be repo-relative: %s"
                    % (prof.get("name"), pattern)
                )
                continue
            try:
                matched = next(iter(root.glob(pattern)), None)
            except (ValueError, NotImplementedError) as exc:
                findings.append(
                    "GLOB: profile '%s' glob invalid (%s): %s"
                    % (prof.get("name"), exc, pattern)
                )
                continue
            if matched is None:
                findings.append(
                    "GLOB: profile '%s' glob matches nothing on disk: %s"
                    % (prof.get("name"), pattern)
                )


def _skillmd_count(root: Path, prof: Dict[str, Any]) -> Optional[int]:
    roots: Set[Path] = set()
    for pattern in prof.get("skill_globs", []):
        prefix = _glob_prefix_dir(root, pattern) if isinstance(pattern, str) else None
        if prefix is not None and prefix.is_dir():
            roots.add(prefix)
    if not roots:
        return None
    seen: Set[Path] = set()
    for base in roots:
        seen.update(base.rglob("SKILL.md"))
    return len(seen)


def _check_cross_install_sh(
    root: Path,
    doc: Dict[str, Any],
    install_text: str,
    findings: List[str],
) -> None:
    profiles: List[Dict[str, Any]] = [p for p in doc["profiles"] if isinstance(p, dict)]
    names = [p.get("name") for p in profiles if isinstance(p.get("name"), str)]
    name_set = set(names)
    if len(names) != len(name_set):
        dupes = sorted({n for n in names if names.count(n) > 1})
        findings.append("SCHEMA: duplicate profile names: %s" % ", ".join(dupes))

    default_parts, dedicated = _parse_install_sh(install_text)

    # (a) default PROFILE assignment.
    declared_default = doc.get("default_profiles")
    if default_parts is None:
        findings.append(
            "DRIFT: could not find default PROFILE=\"...\" assignment in %s" % INSTALL_SH_REL
        )
    elif isinstance(declared_default, list) and declared_default != default_parts:
        findings.append(
            "DRIFT: default_profiles %s != install.sh default %s"
            % (declared_default, default_parts)
        )
    if isinstance(declared_default, list):
        for part in declared_default:
            if part not in name_set:
                findings.append(
                    "DRIFT: default profile '%s' has no manifest entry" % part
                )

    # (b) domain enumeration, both directions.
    domains_dir = root / DOMAINS_REL
    disk_domains: Set[str] = set()
    if domains_dir.is_dir():
        disk_domains = {p.name for p in domains_dir.iterdir() if p.is_dir()}
    else:
        findings.append("DRIFT: domains dir missing on disk: %s" % DOMAINS_REL)
    manifest_domains = name_set - {"core", "frontend"}
    for name in sorted(disk_domains - manifest_domains):
        findings.append(
            "DRIFT: domain dir on disk has no manifest profile: %s" % name
        )
    for name in sorted(manifest_domains - disk_domains):
        findings.append(
            "DRIFT: manifest profile '%s' has no domain dir on disk" % name
        )
    for required in ("core", "frontend"):
        if required not in name_set:
            findings.append("DRIFT: required profile '%s' missing from manifest" % required)

    # (c) stability rule; (d) est_context_cost thresholds.
    derivation = doc.get("derivation") or {}
    cost_rule = derivation.get("est_context_cost_rule") if isinstance(derivation, dict) else None
    low_max, med_max = 9, 25
    if isinstance(cost_rule, dict):
        if isinstance(cost_rule.get("low_max"), int):
            low_max = cost_rule["low_max"]
        if isinstance(cost_rule.get("med_max"), int):
            med_max = cost_rule["med_max"]
    if not (0 <= low_max < med_max):
        findings.append(
            "SCHEMA: est_context_cost_rule thresholds invalid (low_max=%r med_max=%r)"
            % (low_max, med_max)
        )
        return
    stable_set = set(default_parts or []) | dedicated
    for prof in profiles:
        name = prof.get("name")
        if not isinstance(name, str):
            continue
        expected_stability = "stable" if name in stable_set else "experimental"
        if prof.get("stability") in STABILITY_VALUES and prof.get("stability") != expected_stability:
            findings.append(
                "DRIFT: profile '%s' stability '%s' != derived '%s' "
                "(rule: default_profiles UNION dedicated has_profile blocks)"
                % (name, prof.get("stability"), expected_stability)
            )
        count = _skillmd_count(root, prof)
        if count is None:
            continue  # glob findings already cover unresolvable roots
        expected_cost = "low" if count <= low_max else ("med" if count <= med_max else "high")
        if (
            prof.get("est_context_cost") in COST_VALUES
            and prof.get("est_context_cost") != expected_cost
        ):
            findings.append(
                "DRIFT: profile '%s' est_context_cost '%s' != derived '%s' "
                "(%d SKILL.md files; low<=%d med<=%d)"
                % (name, prof.get("est_context_cost"), expected_cost, count, low_max, med_max)
            )


def run_checks(root: Path, manifest_path: Path) -> Tuple[List[str], List[str]]:
    """Return (findings, infra_errors). Empty findings + infra == pass."""
    infra: List[str] = []
    findings: List[str] = []

    if not root.is_dir():
        infra.append("repo root is not a directory: %s" % root)
        return findings, infra
    if not manifest_path.is_file():
        infra.append("manifest not found: %s" % manifest_path)
        return findings, infra
    install_path = root / INSTALL_SH_REL
    if not install_path.is_file():
        infra.append("install.sh not found: %s" % install_path)
        return findings, infra

    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        infra.append("manifest unreadable: %s" % exc)
        return findings, infra
    try:
        install_text = install_path.read_text(encoding="utf-8")
    except OSError as exc:
        infra.append("install.sh unreadable: %s" % exc)
        return findings, infra

    try:
        doc = json.loads(raw)
    except ValueError as exc:
        findings.append("PARSE: manifest is not valid JSON: %s" % exc)
        return findings, infra

    if not _check_top_schema(doc, findings):
        return findings, infra

    profiles = doc["profiles"]
    valid_profiles: List[Dict[str, Any]] = []
    for idx, prof in enumerate(profiles):
        if _check_profile_schema(prof, idx, findings):
            valid_profiles.append(prof)

    stacks = doc["hook_stacks"]
    _check_hook_stacks(root, stacks, findings)
    for prof in valid_profiles:
        for stack_name in prof.get("hook_stacks", []):
            if stack_name not in stacks:
                findings.append(
                    "HOOKS: profile '%s' references undefined hook stack '%s'"
                    % (prof.get("name"), stack_name)
                )
        if "base" not in prof.get("hook_stacks", []):
            findings.append(
                "HOOKS: profile '%s' must include hook stack 'base' "
                "(install.sh installs hooks unconditionally)" % prof.get("name")
            )

    _check_skill_globs(root, valid_profiles, findings)
    _check_cross_install_sh(root, doc, install_text, findings)
    return findings, infra


def main(argv: Optional[List[str]] = None) -> int:
    default_root = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(
        description="Validate scripts/profiles/profiles.json against disk + install.sh (PLAN-153 B4)."
    )
    parser.add_argument("--repo-root", default=str(default_root), help="Repository root")
    parser.add_argument("--manifest", default=None, help="Manifest path (default: <root>/%s)" % MANIFEST_REL)
    parser.add_argument("--json", action="store_true", help="Emit JSON report on stdout")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else root / MANIFEST_REL
    findings, infra = run_checks(root, manifest_path)

    rc = 0
    if findings:
        rc = 1
    if infra:
        rc = 2

    if args.json:
        print(
            json.dumps(
                {
                    "status": {0: "ok", 1: "findings", 2: "infra_error"}[rc],
                    "exit_code": rc,
                    "manifest": str(manifest_path),
                    "findings": findings,
                    "infra_errors": infra,
                },
                indent=2,
            )
        )
    else:
        for line in infra:
            print("INFRA: %s" % line, file=sys.stderr)
        for line in findings:
            print(line)
        if rc == 0:
            print("check-install-profiles: OK (%s)" % manifest_path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
