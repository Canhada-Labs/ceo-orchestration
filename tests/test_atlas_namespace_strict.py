"""Tests for `verify-atlas-binding.py --strict-namespace` (PLAN-095 Wave A.8).

Runs the script as subprocess + asserts exit codes + parses stderr.
Stdlib-only (subprocess + json + sys).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "verify-atlas-binding.py"


def _run(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_default_baseline_still_passes():
    """Regression — adding --strict-namespace flag must not break the
    default (canonical-13) gate."""
    result = _run()
    assert result.returncode == 0, (
        f"verify-atlas-binding.py default mode regressed: "
        f"rc={result.returncode} stderr={result.stderr}"
    )
    assert "PASS" in result.stdout
    assert "canonical-13" in result.stdout


def test_strict_namespace_passes_on_current_registry():
    """PLAN-095 Wave A.8 AC9 — --strict-namespace gate passes against
    HEAD `_ATLAS_REGISTRY` (11 unique IDs all classified atlas|attack-enterprise)."""
    result = _run("--strict-namespace")
    assert result.returncode == 0, (
        f"--strict-namespace FAIL: rc={result.returncode} "
        f"stdout={result.stdout} stderr={result.stderr}"
    )
    assert "PASS" in result.stdout
    assert "11 unique IDs namespace-classified" in result.stdout


def test_strict_namespace_quiet_suppresses_pass_output():
    """--quiet suppresses PASS line but exit code stays 0."""
    result = _run("--strict-namespace", "--quiet")
    assert result.returncode == 0
    # No PASS prose under quiet.
    assert "PASS" not in result.stdout


def test_help_documents_strict_namespace_flag():
    """--help must surface --strict-namespace as a registered option."""
    result = _run("--help")
    assert result.returncode == 0
    assert "--strict-namespace" in result.stdout
    assert "namespace" in result.stdout.lower()


def test_namespace_registry_covers_all_unique_ids():
    """Direct introspection — _NAMESPACE_REGISTRY in verify-atlas-binding.py
    must cover every unique ID in `_lib/audit_emit._ATLAS_REGISTRY`.

    This duplicates the runtime --strict-namespace check but catches
    drift even if the runtime check is bypassed in CI by accident.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_atlas_binding", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inline_namespace = getattr(mod, "_NAMESPACE_REGISTRY", None)
    assert isinstance(inline_namespace, dict)

    # Load actual registry from audit_emit.
    audit_emit_path = (
        REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"
    )
    aspec = importlib.util.spec_from_file_location(
        "audit_emit_for_test", audit_emit_path
    )
    assert aspec is not None and aspec.loader is not None
    amod = importlib.util.module_from_spec(aspec)
    # Need hooks dir on sys.path for cross-module imports.
    hooks_dir = str(audit_emit_path.parent.parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    aspec.loader.exec_module(amod)
    registry = dict(getattr(amod, "_ATLAS_REGISTRY", {}))

    unique_ids = sorted({tid for tid in registry.values()})
    missing = [tid for tid in unique_ids if tid not in inline_namespace]
    assert not missing, (
        f"_NAMESPACE_REGISTRY missing entries for technique IDs: "
        f"{missing!r}. Update verify-atlas-binding.py::_NAMESPACE_REGISTRY "
        f"in the same commit that adds the new binding."
    )


def test_namespace_values_are_valid():
    """Every _NAMESPACE_REGISTRY value must be one of `atlas` or `attack-enterprise`."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_atlas_binding", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inline_namespace = getattr(mod, "_NAMESPACE_REGISTRY", {})
    valid = getattr(mod, "_VALID_NAMESPACES", frozenset())
    assert valid == frozenset({"atlas", "attack-enterprise"})
    invalid = {k: v for k, v in inline_namespace.items() if v not in valid}
    assert not invalid, (
        f"_NAMESPACE_REGISTRY entries with invalid namespace value: "
        f"{invalid!r}. Valid values: {sorted(valid)!r}."
    )


def test_namespace_registry_dual_source_equality():
    """PLAN-095 R2 iter-1 P1 closure (S128) — dual namespace registry
    drift gate.

    Both `verify-atlas-binding._NAMESPACE_REGISTRY` (inline fallback)
    and `audit_emit._ATLAS_NAMESPACE_REGISTRY` (live kernel source,
    post-Patch-1c) must agree. Pre-ceremony state has no kernel
    registry → test PASSES vacuously. Post-ceremony state has both;
    test asserts byte-equal dict.

    This catches the drift trap Codex flagged in iter-1 P1 #8.
    """
    import importlib.util

    # Load inline.
    spec_inline = importlib.util.spec_from_file_location(
        "verify_atlas_binding", SCRIPT
    )
    assert spec_inline is not None and spec_inline.loader is not None
    inline_mod = importlib.util.module_from_spec(spec_inline)
    spec_inline.loader.exec_module(inline_mod)
    inline_ns = dict(getattr(inline_mod, "_NAMESPACE_REGISTRY", {}))

    # Load kernel.
    audit_emit_path = (
        REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"
    )
    aspec = importlib.util.spec_from_file_location(
        "audit_emit_for_dual_test", audit_emit_path
    )
    assert aspec is not None and aspec.loader is not None
    amod = importlib.util.module_from_spec(aspec)
    hooks_dir = str(audit_emit_path.parent.parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    aspec.loader.exec_module(amod)
    kernel_ns = getattr(amod, "_ATLAS_NAMESPACE_REGISTRY", None)

    if kernel_ns is None:
        # Pre-ceremony state — kernel registry not yet provisioned.
        # Test passes vacuously; runtime fallback to inline is correct.
        return

    kernel_ns_dict = dict(kernel_ns)
    assert inline_ns == kernel_ns_dict, (
        f"Dual namespace registry DRIFT detected.\n"
        f"verify-atlas-binding._NAMESPACE_REGISTRY = {sorted(inline_ns.items())}\n"
        f"audit_emit._ATLAS_NAMESPACE_REGISTRY      = {sorted(kernel_ns_dict.items())}\n"
        f"Update both surfaces in the same commit per "
        f"`.claude/plans/PLAN-095/PATCH-audit_emit.py.diff.md` §Patch 1c."
    )
