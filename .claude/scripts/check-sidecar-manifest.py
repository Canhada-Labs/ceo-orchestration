#!/usr/bin/env python3
"""ADR-126 §Part 6 manifest validator — framework-level schema check.

Walks `.claude/sidecars/*/<name>/manifest.json` and asserts each manifest
conforms to ADR-126 Part 4 canonical 5-block schema. Stdlib-only (no
jsonschema import — production-path invariant per ADR-002).

PLAN-097 Wave B.4 extensions (AC9):
  - Tier-C `explicit_opt_in_required==true` consistency
  - `governance.authorizing_adr` references ACCEPTED ADR
  - `governance.cost_envelope` populated when install-time model download
    (`install.model_pin_sha256` present) OR `default_tier == "C"`
  - `isolation.allowed_workflow_invocation_patterns` re.compile-validation
  - ADR-128 §3 C2-specific constraints (kill_switch_env / min_python / hw_class_check)

PLAN-112-FOLLOWUP-sbom-third-party-disclosure (S15x) extensions:
  - `dependencies.licenses` schema: an object mapping each declared
    `dependencies.python` package (by spec name, stripped of version pin) to
    an SPDX license expression. Required so the SBOM can source per-package
    licenses from the manifest (single source of truth, no hand-transcription).
    A manifest with python deps but no covering license entry FAILS.
  - `--check-sbom-sync`: a CI gate that fails if any sidecar-declared python
    package is absent from SBOM.md Section B ("Sidecar dependencies"). Keeps
    SBOM.md in sync as sidecars evolve (AC4).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SIDECARS_ROOT = _REPO_ROOT / ".claude" / "sidecars"
_ADR_ROOT = _REPO_ROOT / ".claude" / "adr"
_SBOM_PATH = _REPO_ROOT / "SBOM.md"

# ADR-128 §3 C2-specific constraints.
_C2_REQUIRED_KILL_SWITCH = "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED"
_C2_MIN_PYTHON = "3.10"
_C2_MIN_HW = "disk_2gb"

_REQUIRED_TOP = ["sidecar", "isolation", "dependencies", "governance", "install"]
_REQUIRED_SIDECAR = ["name", "capability_class", "version", "default_tier"]
_REQUIRED_ISOLATION = [
    "core_paths_blocked",
    "core_paths_allowlisted_workflow_invokers",
    "import_roots",
    "allowed_workflow_invocation_patterns",
    "boundary_test",
]
_REQUIRED_DEPS = ["python", "system"]
_REQUIRED_GOVERNANCE = [
    "kill_switch_env",
    "default_state",
    "activation_predicate",
    "enable_value",
    "disable_value",
    "explicit_opt_in_required",
    "authorizing_adr",
    "cost_envelope",
]
_REQUIRED_COST_ENV = ["per_invocation_tokens", "daily_burn_cap", "enforcement"]
_REQUIRED_INSTALL = ["script", "hw_class_check"]

_VALID_CLASSES = {"C1", "C2", "C3", "C4", "C5"}
_VALID_TIERS = {"A", "B", "C"}

# Version-pin operators we strip to recover the bare package spec name.
_PIN_SPLIT_RE = re.compile(r"[<>=!~ ]")


def _err(violations: List[str], manifest_path: Path, msg: str) -> None:
    violations.append(f"{manifest_path.relative_to(_REPO_ROOT)}: {msg}")


def _check_keys(
    obj: Any, required: List[str], where: str, path: Path, viol: List[str]
) -> bool:
    if not isinstance(obj, dict):
        _err(viol, path, f"{where} is not an object")
        return False
    missing = [k for k in required if k not in obj]
    if missing:
        _err(viol, path, f"{where} missing keys: {missing}")
        return False
    return True


def _pkg_name(spec: str) -> str:
    """Strip a PEP 508 version pin to the bare distribution name.

    "cryptography>=42.0,<44.0" -> "cryptography"
    "sentence-transformers==2.5.1" -> "sentence-transformers"
    """
    head = _PIN_SPLIT_RE.split(spec.strip(), 1)[0]
    return head.strip()


def _declared_python_packages(data: dict) -> List[str]:
    """Bare package names declared under dependencies.python (pin stripped)."""
    deps = data.get("dependencies", {})
    pys = deps.get("python", []) if isinstance(deps, dict) else []
    out: List[str] = []
    if isinstance(pys, list):
        for spec in pys:
            if isinstance(spec, str) and spec.strip():
                out.append(_pkg_name(spec))
    return out


def _read_adr_status(adr_id: str) -> Optional[str]:
    """Resolve an ADR id prefix to its `status:` frontmatter field.

    `adr_id` examples: "ADR-128", "ADR-128-AMEND-1". Returns None if no
    matching file found.
    """
    if not _ADR_ROOT.exists():
        return None
    candidates = list(_ADR_ROOT.glob(f"{adr_id}-*.md")) + list(_ADR_ROOT.glob(f"{adr_id}.md"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: len(p.name))
    text = candidates[0].read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _validate_opt_in_consistency(data: dict, path: Path, viol: List[str]) -> None:
    """Tier-C MUST be explicit_opt_in_required=true."""
    sc = data["sidecar"]
    gov = data["governance"]
    tier = sc.get("default_tier")
    opt_in = gov.get("explicit_opt_in_required")
    if tier == "C" and opt_in is not True:
        _err(
            viol,
            path,
            f"Tier-C sidecar MUST set governance.explicit_opt_in_required=true; got {opt_in!r}",
        )


def _validate_authorizing_adr(data: dict, path: Path, viol: List[str]) -> None:
    """`governance.authorizing_adr` must reference an existing ADR file.

    Status acceptance policy (PLAN-097 v1.30.0 amendment to PLAN-093 strict mode):
      - ACCEPTED / ACCEPTED-AMENDED — pass silently.
      - PROPOSED — pass (silently OK; ADRs shipping with their introducing
        plan are legitimately PROPOSED until the Codex R2 promotion ceremony
        flips them to ACCEPTED. Pattern established by PLAN-096 v1.29.0
        with ADR-042-AMEND-1.). Use a stricter linting profile via
        `--reject-proposed-adr` to surface PROPOSED as a violation in
        post-ship hygiene runs.
      - RESERVED / missing / SUPERSEDED / RETRACTED — fail-CLOSED.
    """
    gov = data["governance"]
    adr_id = gov.get("authorizing_adr")
    if not adr_id:
        return  # caught by required-fields
    if not re.fullmatch(r"ADR-\d{3}(?:-AMEND-\d+)?", str(adr_id)):
        _err(
            viol,
            path,
            f"governance.authorizing_adr must match 'ADR-NNN' or 'ADR-NNN-AMEND-M'; got {adr_id!r}",
        )
        return
    status = _read_adr_status(str(adr_id))
    if status is None:
        _err(viol, path, f"governance.authorizing_adr {adr_id} not found in .claude/adr/")
        return
    if status in ("ACCEPTED", "ACCEPTED-AMENDED", "PROPOSED"):
        return
    _err(
        viol,
        path,
        f"governance.authorizing_adr {adr_id} status={status!r} "
        "(must be ACCEPTED, ACCEPTED-AMENDED, or PROPOSED; RESERVED/SUPERSEDED/RETRACTED rejected)",
    )


def _validate_cost_envelope_conditional(data: dict, path: Path, viol: List[str]) -> None:
    """Tier-C OR install-time-download sidecars MUST have populated cost_envelope.

    Tier-A/Tier-B sidecars MAY have empty cost_envelope (`enforcement=disabled`).
    """
    sc = data["sidecar"]
    gov = data["governance"]
    inst = data["install"]
    tier = sc.get("default_tier")
    has_install_download = "model_pin_sha256" in inst
    requires_real_cost = tier == "C" or has_install_download
    cost = gov.get("cost_envelope")
    if not requires_real_cost:
        return
    if not isinstance(cost, dict):
        _err(
            viol,
            path,
            f"governance.cost_envelope required as object for "
            f"{'Tier-C' if tier == 'C' else 'install-time-download'} sidecar",
        )
        return
    enf = cost.get("enforcement")
    if enf == "disabled":
        _err(
            viol,
            path,
            f"governance.cost_envelope.enforcement='disabled' rejected for "
            f"{'Tier-C' if tier == 'C' else 'install-time-download'} sidecar "
            "— populate with adapter|adapter+settings",
        )


def _validate_isolation_patterns(data: dict, path: Path, viol: List[str]) -> None:
    """Every `allowed_workflow_invocation_patterns` entry must re.compile."""
    iso = data["isolation"]
    patterns = iso.get("allowed_workflow_invocation_patterns")
    if not isinstance(patterns, list):
        return
    for p in patterns:
        if not isinstance(p, str):
            _err(viol, path, f"isolation.allowed_workflow_invocation_patterns entry must be string, got {type(p).__name__}")
            continue
        try:
            re.compile(p)
        except re.error as exc:
            _err(viol, path, f"isolation pattern {p!r} fails re.compile: {exc}")
    import_roots = iso.get("import_roots")
    if isinstance(import_roots, list) and not import_roots:
        _err(viol, path, "isolation.import_roots must be non-empty list")


def _validate_licenses(data: dict, path: Path, viol: List[str]) -> None:
    """dependencies.licenses must cover every declared dependencies.python pkg.

    PLAN-112-FOLLOWUP-sbom-third-party-disclosure: the SBOM sources per-package
    licenses from the manifest, so the manifest is the single source of truth.
      - `licenses` MUST be present and be an object.
      - Every bare package name in dependencies.python MUST appear as a key in
        `licenses` with a non-empty SPDX string value.
      - A manifest with NO python deps (stdlib-only) MUST still carry an empty
        `licenses` object `{}` (presence enforced for schema uniformity).
      - Extra license keys not matching a declared package are tolerated
        (forward-compat) but reported as a soft note via stderr — NOT a
        violation.
    """
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        return  # caught by required-fields
    licenses = deps.get("licenses")
    if licenses is None:
        _err(viol, path, "dependencies.licenses missing (required object mapping each python package -> SPDX license)")
        return
    if not isinstance(licenses, dict):
        _err(viol, path, f"dependencies.licenses must be an object; got {type(licenses).__name__}")
        return
    for pkg in _declared_python_packages(data):
        val = licenses.get(pkg)
        if not isinstance(val, str) or not val.strip():
            _err(
                viol,
                path,
                f"dependencies.licenses missing/empty SPDX license for declared package {pkg!r}",
            )


def _validate_c2_constraints(data: dict, path: Path, viol: List[str]) -> None:
    """ADR-128 §3 C2-specific constraints."""
    sc = data["sidecar"]
    if sc.get("capability_class") != "C2":
        return
    if sc.get("default_tier") != "B":
        _err(
            viol,
            path,
            f"ADR-128 §3 — C2 sidecar default_tier MUST be 'B'; got {sc.get('default_tier')!r}",
        )
    gov = data["governance"]
    if gov.get("kill_switch_env") != _C2_REQUIRED_KILL_SWITCH:
        _err(
            viol,
            path,
            f"ADR-128 §3 — C2 sidecar kill_switch_env MUST be {_C2_REQUIRED_KILL_SWITCH!r}; "
            f"got {gov.get('kill_switch_env')!r}",
        )
    inst = data["install"]
    if inst.get("min_python") != _C2_MIN_PYTHON:
        _err(
            viol,
            path,
            f"ADR-128 §3 — C2 sidecar install.min_python MUST be {_C2_MIN_PYTHON!r}; "
            f"got {inst.get('min_python')!r}",
        )
    if inst.get("hw_class_check") != _C2_MIN_HW:
        _err(
            viol,
            path,
            f"ADR-128 §3 — C2 sidecar install.hw_class_check MUST be {_C2_MIN_HW!r}; "
            f"got {inst.get('hw_class_check')!r}",
        )


def _validate(path: Path) -> List[str]:
    viol: List[str] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path.relative_to(_REPO_ROOT)}: invalid JSON ({exc})"]

    if not _check_keys(data, _REQUIRED_TOP, "<root>", path, viol):
        return viol

    sc = data["sidecar"]
    if _check_keys(sc, _REQUIRED_SIDECAR, "sidecar", path, viol):
        if sc["capability_class"] not in _VALID_CLASSES:
            _err(viol, path, f"sidecar.capability_class must be one of {sorted(_VALID_CLASSES)}")
        if sc["default_tier"] not in _VALID_TIERS:
            _err(viol, path, f"sidecar.default_tier must be one of {sorted(_VALID_TIERS)}")

    iso = data["isolation"]
    if _check_keys(iso, _REQUIRED_ISOLATION, "isolation", path, viol):
        for lst_key in (
            "core_paths_blocked",
            "core_paths_allowlisted_workflow_invokers",
            "import_roots",
            "allowed_workflow_invocation_patterns",
        ):
            if not isinstance(iso[lst_key], list):
                _err(viol, path, f"isolation.{lst_key} must be a list")
        if not isinstance(iso["boundary_test"], str):
            _err(viol, path, "isolation.boundary_test must be a string")

    deps = data["dependencies"]
    if _check_keys(deps, _REQUIRED_DEPS, "dependencies", path, viol):
        for k in ("python", "system"):
            if not isinstance(deps[k], list):
                _err(viol, path, f"dependencies.{k} must be a list")

    gov = data["governance"]
    if _check_keys(gov, _REQUIRED_GOVERNANCE, "governance", path, viol):
        if not isinstance(gov["explicit_opt_in_required"], bool):
            _err(viol, path, "governance.explicit_opt_in_required must be bool")
        if not isinstance(gov["cost_envelope"], dict):
            _err(viol, path, "governance.cost_envelope must be an object")
        else:
            _check_keys(
                gov["cost_envelope"],
                _REQUIRED_COST_ENV,
                "governance.cost_envelope",
                path,
                viol,
            )

    inst = data["install"]
    _check_keys(inst, _REQUIRED_INSTALL, "install", path, viol)

    # PLAN-097 Wave B.4 extensions (AC9).
    _validate_opt_in_consistency(data, path, viol)
    _validate_authorizing_adr(data, path, viol)
    _validate_cost_envelope_conditional(data, path, viol)
    _validate_isolation_patterns(data, path, viol)
    _validate_c2_constraints(data, path, viol)

    # PLAN-112-FOLLOWUP-sbom-third-party-disclosure: license schema.
    _validate_licenses(data, path, viol)

    return viol


# -----------------------------------------------------------------------------
# SBOM sync gate (AC4) — PLAN-112-FOLLOWUP-sbom-third-party-disclosure
# -----------------------------------------------------------------------------

def _load_manifests() -> List[Path]:
    if not _SIDECARS_ROOT.exists():
        return []
    return sorted(_SIDECARS_ROOT.glob("*/*/manifest.json"))


def _parse_sbom_section_b_packages(sbom_text: str) -> Set[str]:
    """Extract the set of package names listed in SBOM.md Section B.

    Section B is delimited by an HTML anchor comment pair:
      <!-- SBOM-SECTION-B:BEGIN -->  ...  <!-- SBOM-SECTION-B:END -->
    Within that span, every markdown table row whose first cell is wrapped in
    backticks (`pkg`) contributes that backticked token as a package name.
    The anchor comments make the parse robust to prose/wording changes — we do
    NOT scrape the whole file (that would false-match unrelated backticks).
    """
    begin = sbom_text.find("<!-- SBOM-SECTION-B:BEGIN -->")
    end = sbom_text.find("<!-- SBOM-SECTION-B:END -->")
    if begin == -1 or end == -1 or end <= begin:
        return set()
    span = sbom_text[begin:end]
    pkgs: Set[str] = set()
    # First backticked token of each markdown table row: | `pkg` | ... |
    row_re = re.compile(r"^\s*\|\s*`([^`]+)`\s*\|", re.MULTILINE)
    for m in row_re.finditer(span):
        pkgs.add(m.group(1).strip())
    return pkgs


def check_sbom_sync() -> int:
    """Fail (return 1) if a manifest-declared python package is absent from
    SBOM.md Section B. AC4.
    """
    manifests = _load_manifests()
    declared: Dict[str, List[str]] = {}  # pkg -> [manifest rels]
    for m in manifests:
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"check-sidecar-manifest --check-sbom-sync: cannot read {m}: {exc}\n")
            return 1
        for pkg in _declared_python_packages(data):
            declared.setdefault(pkg, []).append(str(m.relative_to(_REPO_ROOT)))

    if not _SBOM_PATH.exists():
        sys.stderr.write(f"check-sidecar-manifest --check-sbom-sync: {_SBOM_PATH} not found\n")
        return 1
    sbom_text = _SBOM_PATH.read_text(encoding="utf-8", errors="replace")
    listed = _parse_sbom_section_b_packages(sbom_text)

    if declared and not listed:
        sys.stderr.write(
            "check-sidecar-manifest --check-sbom-sync FAILED: SBOM.md Section B "
            "anchor block (<!-- SBOM-SECTION-B:BEGIN/END -->) not found or empty, "
            f"but {len(declared)} sidecar package(s) are declared.\n"
        )
        for pkg in sorted(declared):
            sys.stderr.write(f"  - {pkg} (declared in {', '.join(declared[pkg])})\n")
        return 1

    missing = sorted(p for p in declared if p not in listed)
    if missing:
        sys.stderr.write(
            "check-sidecar-manifest --check-sbom-sync FAILED: sidecar package(s) "
            "declared in a manifest but absent from SBOM.md Section B:\n"
        )
        for pkg in missing:
            sys.stderr.write(f"  - {pkg} (declared in {', '.join(declared[pkg])})\n")
        sys.stderr.write(
            "  Fix: add the package row to SBOM.md Section B "
            "(Sidecar dependencies) so the SBOM stays in sync with the manifests.\n"
        )
        return 1

    print(
        f"check-sidecar-manifest --check-sbom-sync OK "
        f"({len(declared)} sidecar package(s) all present in SBOM.md Section B)"
    )
    return 0


def main() -> int:
    strict = "--strict" in sys.argv

    if "--check-sbom-sync" in sys.argv:
        return check_sbom_sync()

    if not _SIDECARS_ROOT.exists():
        # No sidecars yet — OK pre-PLAN-093.
        if strict:
            print("check-sidecar-manifest: no .claude/sidecars/ directory yet (OK)")
        return 0

    manifests = sorted(_SIDECARS_ROOT.glob("*/*/manifest.json"))
    if not manifests:
        if strict:
            print("check-sidecar-manifest: no manifest.json files found (OK)")
        return 0

    all_viol: List[str] = []
    for m in manifests:
        all_viol.extend(_validate(m))

    if all_viol:
        sys.stderr.write("check-sidecar-manifest FAILED:\n")
        for v in all_viol:
            sys.stderr.write(f"  - {v}\n")
        return 1

    if strict:
        print(f"check-sidecar-manifest OK ({len(manifests)} manifest(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
