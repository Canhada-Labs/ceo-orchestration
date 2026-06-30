"""Unit tests for ``check-audit-registry-coverage.py``.

PLAN-013 Phase A.6 + ADJ-021 (QA Architect §S10 HIGH consensus).
Subclasses ``TestEnvContext`` from ``_lib/testing.py`` per CLAUDE.md §5
Critical Rules + PLAN-013 consensus §S11. Every test runs in an
isolated tmp ``project_dir``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = SCRIPT_ROOT / "scripts" / "check-audit-registry-coverage.py"
REPO_ROOT = SCRIPT_ROOT.parent


# ---------------------------------------------------------------------------
# Fixture helpers — build a mini-repo with known drift scenarios
# ---------------------------------------------------------------------------


def _write_audit_emit(
    tmpdir: Path,
    known_actions: list,
    emit_defs_extra: list = None,
) -> Path:
    """Write a minimal ``_lib/audit_emit.py`` under tmpdir.

    ``known_actions`` populates ``_KNOWN_ACTIONS``. ``emit_defs_extra`` is
    a list of action names for which to generate ``def emit_<name>`` stubs
    ON TOP of the ones implied by ``known_actions``. Use it to simulate
    "function defined but not registered" scenarios.
    """
    lib_dir = tmpdir / ".claude" / "hooks" / "_lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    set_body = ", ".join(f'"{name}"' for name in known_actions)
    emit_funcs = []
    # Generate a stub for every registered action
    for name in known_actions:
        emit_funcs.append(
            f"def emit_{name}(**kwargs):\n"
            f"    pass\n"
        )
    # Plus any extras (simulating unregistered defs)
    for name in (emit_defs_extra or []):
        emit_funcs.append(
            f"def emit_{name}(**kwargs):\n"
            f"    pass\n"
        )

    content = (
        '"""fixture audit_emit"""\n\n'
        f"_KNOWN_ACTIONS = {{{set_body}}}\n\n"
        + "\n".join(emit_funcs)
    )
    path = lib_dir / "audit_emit.py"
    path.write_text(content, encoding="utf-8")

    # Ensure _lib is a package
    init = lib_dir / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")
    return path


def _write_schema(tmpdir: Path, actions: list, malformed: bool = False) -> Path:
    """Write a minimal ``SPEC/v1/audit-log.schema.md`` with a registered-
    fields table. ``malformed=True`` omits the table to trigger exit 2.
    """
    spec_dir = tmpdir / "SPEC" / "v1"
    spec_dir.mkdir(parents=True, exist_ok=True)

    if malformed:
        body = "# SPEC v1 — audit-log schema\n\n(no table here)\n"
    else:
        rows = ["| `action` | required fields |", "|---|---|"]
        for name in actions:
            rows.append(f"| `{name}` (v2.5) | `action`, `ts` |")
        body = (
            "# SPEC v1 — audit-log.schema\n\n"
            "### Required fields per v2 action\n\n"
            + "\n".join(rows)
            + "\n\n"
            "### Additivity\n\nTrailing prose after the table.\n"
        )
    path = spec_dir / "audit-log.schema.md"
    path.write_text(body, encoding="utf-8")
    return path


def _write_caller(tmpdir: Path, relative: str, body: str) -> Path:
    """Write an arbitrary .py file under .claude/scripts/ or .claude/hooks/."""
    path = tmpdir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _run(
    tmpdir: Path,
    verbose: bool = False,
    extra_args: "list | None" = None,
) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "--repo-root", str(tmpdir)]
    if verbose:
        cmd.append("--verbose")
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True)


def _golden_path(tmpdir: Path) -> Path:
    """Path to the on-disk golden inventory file inside a fixture repo."""
    return tmpdir / ".claude" / "data" / "audit-registry.golden.txt"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuditRegistryCoverage(TestEnvContext):

    def test_clean_repo_passes(self) -> None:
        """Registry, schema, and call sites all in sync → exit 0."""
        _write_audit_emit(self.project_dir, ["action_alpha", "action_beta"])
        _write_schema(self.project_dir, ["action_alpha", "action_beta"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/caller.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_action_alpha(foo=1)\n"
            "audit_emit.emit_action_beta(bar=2)\n",
        )
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn("OK", result.stdout)

    def test_action_in_code_but_not_schema_fails(self) -> None:
        """Registered in _KNOWN_ACTIONS but missing schema row → exit 1."""
        _write_audit_emit(self.project_dir, ["alpha", "beta"])
        _write_schema(self.project_dir, ["alpha"])  # missing beta
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing from SPEC/v1/audit-log.schema.md", result.stderr)
        self.assertIn("beta", result.stderr)

    def test_action_in_schema_but_not_code_fails(self) -> None:
        """Documented in schema but not in registry → exit 1."""
        _write_audit_emit(self.project_dir, ["alpha"])
        _write_schema(self.project_dir, ["alpha", "gamma"])  # extra gamma
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing from _KNOWN_ACTIONS", result.stderr)
        self.assertIn("gamma", result.stderr)

    def test_orphan_emit_call_fails(self) -> None:
        """Call site to emit_<name> with <name> not in registry → exit 1."""
        _write_audit_emit(self.project_dir, ["registered_action"])
        _write_schema(self.project_dir, ["registered_action"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/bad.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_orphan_action(foo=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Orphan emit_", result.stderr)
        self.assertIn("emit_orphan_action", result.stderr)
        self.assertIn("bad.py:2", result.stderr)

    def test_emit_in_docstring_is_ignored(self) -> None:
        """emit_foo() mentioned in a docstring must NOT trigger orphan."""
        _write_audit_emit(self.project_dir, ["registered"])
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/docy.py",
            '"""Module docstring mentioning emit_foo() and emit_bar()."""\n'
            "\n"
            "def helper():\n"
            '    """Example: emit_baz() would not actually run here."""\n'
            "    from _lib import audit_emit\n"
            "    audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_emit_in_comment_is_ignored(self) -> None:
        """# emit_foo() in a comment must NOT trigger orphan."""
        _write_audit_emit(self.project_dir, ["registered"])
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/commented.py",
            "# audit_emit.emit_phantom_foo(x=1) — commented out\n"
            "# emit_phantom_bar(x=2) — also comment\n"
            "from _lib import audit_emit\n"
            "audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_multiple_drift_all_reported(self) -> None:
        """Multi-category drift: every category surfaces in output."""
        _write_audit_emit(
            self.project_dir,
            ["alpha", "beta"],
        )
        _write_schema(self.project_dir, ["alpha", "gamma"])  # alpha ok; beta/gamma drift
        _write_caller(
            self.project_dir,
            ".claude/scripts/multi.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_alpha(x=1)\n"
            "audit_emit.emit_not_registered(x=2)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        # Schema missing beta
        self.assertIn("beta", result.stderr)
        # Code missing gamma
        self.assertIn("gamma", result.stderr)
        # Orphan emit_not_registered
        self.assertIn("emit_not_registered", result.stderr)

    def test_missing_audit_emit_file_returns_2(self) -> None:
        """audit_emit.py absent → exit 2 internal error."""
        # Only write schema
        _write_schema(self.project_dir, ["x"])
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("audit_emit.py not found", result.stderr)

    def test_malformed_schema_returns_2(self) -> None:
        """Schema file exists but has no table → exit 2."""
        _write_audit_emit(self.project_dir, ["x"])
        _write_schema(self.project_dir, [], malformed=True)
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no action rows found", result.stderr)

    def test_case_sensitivity_emit_uppercase_ignored(self) -> None:
        """Emit_Foo / emit_FOO must NOT be treated as emit_foo.

        The check only matches lowercase snake_case ``emit_<name>``;
        a CamelCase or ALL-CAPS variant is treated as an unrelated
        helper (no collision with the registry) because the suffix
        regex ``^[a-z][a-z0-9_]*$`` rejects it.
        """
        _write_audit_emit(self.project_dir, ["registered"])
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/case.py",
            "from _lib import audit_emit\n"
            "# These are unrelated helpers; the check ignores non-snake_case:\n"
            "def Emit_Foo():\n"
            "    pass\n"
            "def emit_BAR_CAPS():\n"
            "    pass\n"
            "Emit_Foo()\n"
            "emit_BAR_CAPS()\n"
            "audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_from_import_alias_resolved(self) -> None:
        """from _lib.audit_emit import emit_foo as _f → _f() resolves to emit_foo."""
        _write_audit_emit(self.project_dir, ["foo"])
        _write_schema(self.project_dir, ["foo"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/aliased.py",
            "from _lib.audit_emit import emit_foo as _f\n"
            "_f(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_module_alias_resolved(self) -> None:
        """from _lib import audit_emit as _ae → _ae.emit_foo(...) resolves."""
        _write_audit_emit(self.project_dir, ["foo"])
        _write_schema(self.project_dir, ["foo"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/mod_alias.py",
            "from _lib import audit_emit as _ae\n"
            "_ae.emit_foo(x=1)\n"
            "_ae.emit_orphan(x=2)\n",  # second call is orphan
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("emit_orphan", result.stderr)

    def test_unrelated_emit_prefix_ignored(self) -> None:
        """emit_json / emit_decision / emit_deny in unrelated contexts ignored.

        This is the critical false-positive guard: the framework has many
        helpers that use the ``emit_`` prefix but are NOT audit emitters
        (check_*.py use ``_lib.contract.emit_decision``; benchmark uses
        ``emit_json``/``emit_markdown`` formatters; mcp-server uses
        locally-scoped ``emit_deny``/``emit_invoke`` wrappers). The check
        must only flag calls that import-resolve to ``_lib.audit_emit``.
        """
        _write_audit_emit(self.project_dir, ["registered"])
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/hooks/check_fake.py",
            # No import of audit_emit at all — these are unrelated helpers.
            "from some.other.module import contract\n"
            "def local_wrapper(event):\n"
            "    return emit_decision(event)  # bare call, not audit_emit\n"
            "def emit_deny(x):\n"
            "    return x\n"
            "def emit_invoke(x):\n"
            "    return x\n"
            "def emit_json(x):\n"
            "    return x\n"
            "emit_deny('test')\n"
            "emit_invoke('test')\n"
            "emit_json('test')\n"
            "contract.emit_decision({})\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_unregistered_def_flagged(self) -> None:
        """def emit_<name> in audit_emit.py without <name> in registry → exit 1."""
        # alpha registered; def emit_beta exists but beta is NOT in registry
        _write_audit_emit(
            self.project_dir,
            ["alpha"],
            emit_defs_extra=["beta"],
        )
        _write_schema(self.project_dir, ["alpha"])
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not in _KNOWN_ACTIONS", result.stderr)
        self.assertIn("emit_beta", result.stderr)

    def test_tests_and_fixtures_directories_skipped(self) -> None:
        """Calls under /tests/ and /fixtures/ must NOT be scanned.

        Tests intentionally reference non-registered names for isolation
        scenarios, and fixtures are static sample payloads.
        """
        _write_audit_emit(self.project_dir, ["registered"])
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/tests/test_something.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_nonsense_for_test(x=1)\n",
        )
        _write_caller(
            self.project_dir,
            ".claude/scripts/tests/fixtures/sample.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_also_nonsense(x=2)\n",
        )
        # And a real call site that IS registered
        _write_caller(
            self.project_dir,
            ".claude/scripts/real.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    # -----------------------------------------------------------------
    # Codex audit-v3 (Session 76, DIM-04 finding 2) regression tests
    # for emit_generic literal + getattr-alias resolution.
    # -----------------------------------------------------------------

    def test_emit_generic_literal_positional_orphan_detected(self) -> None:
        """``emit_generic("unknown_action", ...)`` → orphan exit 1."""
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/dispatch.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_generic('unregistered_via_generic', foo=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("emit_unregistered_via_generic", result.stderr)
        self.assertIn("dispatch.py:2", result.stderr)

    def test_emit_generic_literal_kwarg_orphan_detected(self) -> None:
        """``emit_generic(action="unknown_action", ...)`` → orphan exit 1."""
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/dispatch_kw.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_generic(action='kw_form_unknown', x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("emit_kw_form_unknown", result.stderr)
        self.assertIn("dispatch_kw.py:2", result.stderr)

    def test_emit_generic_literal_registered_passes(self) -> None:
        """``emit_generic("registered", ...)`` → exit 0 when registered."""
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/ok.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_generic('registered', foo=1)\n"
            "audit_emit.emit_generic(action='registered', bar=2)\n",
        )
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_emit_generic_dynamic_dispatch_silently_skipped(self) -> None:
        """``emit_generic(var, ...)`` cannot be statically verified — no orphan."""
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/dynamic.py",
            "from _lib import audit_emit\n"
            "def fire(action_name):\n"
            "    audit_emit.emit_generic(action_name, foo=1)\n"
            "fire('whatever')\n"
            "audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_getattr_alias_resolves_to_emit_generic(self) -> None:
        """``e = getattr(audit_emit, "emit_generic", None); e(action="x", ...)``."""
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/getattr_alias.py",
            "from _lib import audit_emit\n"
            "emitter = getattr(audit_emit, 'emit_generic', None)\n"
            "if emitter is not None:\n"
            "    emitter(action='unregistered_via_alias', x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("emit_unregistered_via_alias", result.stderr)

    def test_emit_generic_def_excluded_from_unregistered_check(self) -> None:
        """``def emit_generic(...)`` itself is a dispatcher, not an action.

        It must NOT be flagged as unregistered just because the literal
        action ``generic`` is absent from ``_KNOWN_ACTIONS``.
        """
        _write_audit_emit(
            self.project_dir,
            ["registered"],
            emit_defs_extra=["generic"],
        )
        _write_schema(self.project_dir, ["registered"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/clean.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_registered(x=1)\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}",
        )

    def test_output_format_includes_file_line(self) -> None:
        """Every drift item has a file:line reference for jump-to-error."""
        _write_audit_emit(self.project_dir, ["alpha"])
        _write_schema(self.project_dir, ["alpha"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/linecheck.py",
            "from _lib import audit_emit\n"
            "\n"
            "\n"
            "\n"
            "audit_emit.emit_notreg(x=1)  # line 5\n",
        )
        result = _run(self.project_dir)
        self.assertEqual(result.returncode, 1)
        # linecheck.py:5 must appear verbatim
        self.assertIn("linecheck.py:5", result.stderr)


class TestGoldenInventory(TestEnvContext):
    """PLAN-133 E8 — generated-SPEC golden-inventory drift guard.

    The golden is generated FROM the typed helpers (``_KNOWN_ACTIONS`` +
    ``def emit_<name>``); ``--check`` asserts the on-disk golden matches it
    byte-for-byte. These tests prove: round-trip write→check, drift after a
    registry change, absent-golden, default-OFF (no golden gate unless
    ``--check``), internal-error propagation, and mutual-exclusion.
    """

    def test_write_golden_then_check_passes(self) -> None:
        """--write-golden creates the file; --check then passes (round-trip)."""
        _write_audit_emit(self.project_dir, ["alpha", "beta", "gamma"])
        _write_schema(self.project_dir, ["alpha", "beta", "gamma"])
        wresult = _run(self.project_dir, extra_args=["--write-golden"])
        self.assertEqual(wresult.returncode, 0, msg=f"stderr={wresult.stderr}")
        self.assertTrue(_golden_path(self.project_dir).is_file())
        cresult = _run(self.project_dir, verbose=True, extra_args=["--check"])
        self.assertEqual(cresult.returncode, 0, msg=f"stderr={cresult.stderr}")
        self.assertIn("OK", cresult.stdout)

    def test_golden_content_is_sorted_registered_actions(self) -> None:
        """Golden body = sorted _KNOWN_ACTIONS, one per line, with header."""
        _write_audit_emit(self.project_dir, ["zeta", "alpha", "mu"])
        _write_schema(self.project_dir, ["zeta", "alpha", "mu"])
        _run(self.project_dir, extra_args=["--write-golden"])
        text = _golden_path(self.project_dir).read_text(encoding="utf-8")
        lines = text.splitlines()
        body = [ln for ln in lines if not ln.startswith("#")]
        self.assertEqual(body, ["alpha", "mu", "zeta"])
        # Header carries a count line and a regenerate hint.
        self.assertTrue(any(ln.startswith("# count: 3") for ln in lines))
        self.assertTrue(any("--write-golden" in ln for ln in lines))
        # Trailing newline preserved.
        self.assertTrue(text.endswith("\n"))

    def test_check_detects_registry_change_drift(self) -> None:
        """Adding an action without regenerating the golden → --check exit 1 + diff."""
        _write_audit_emit(self.project_dir, ["alpha", "beta"])
        _write_schema(self.project_dir, ["alpha", "beta"])
        _run(self.project_dir, extra_args=["--write-golden"])
        # Now the registry grows by one action; golden is stale.
        _write_audit_emit(self.project_dir, ["alpha", "beta", "delta"])
        _write_schema(self.project_dir, ["alpha", "beta", "delta"])
        result = _run(self.project_dir, extra_args=["--check"])
        self.assertEqual(result.returncode, 1, msg=f"stderr={result.stderr}")
        self.assertIn("GOLDEN DRIFT", result.stderr)
        self.assertIn("delta", result.stderr)
        self.assertIn("--write-golden", result.stderr)

    def test_check_detects_removed_action_drift(self) -> None:
        """Removing an action without regen → --check exit 1 (stale line)."""
        _write_audit_emit(self.project_dir, ["alpha", "beta", "gamma"])
        _write_schema(self.project_dir, ["alpha", "beta", "gamma"])
        _run(self.project_dir, extra_args=["--write-golden"])
        _write_audit_emit(self.project_dir, ["alpha", "beta"])  # gamma gone
        _write_schema(self.project_dir, ["alpha", "beta"])
        result = _run(self.project_dir, extra_args=["--check"])
        self.assertEqual(result.returncode, 1, msg=f"stderr={result.stderr}")
        self.assertIn("GOLDEN DRIFT", result.stderr)
        self.assertIn("gamma", result.stderr)

    def test_check_missing_golden_is_drift_not_infra(self) -> None:
        """--check with no golden on disk → exit 1 (treated as drift)."""
        _write_audit_emit(self.project_dir, ["alpha"])
        _write_schema(self.project_dir, ["alpha"])
        self.assertFalse(_golden_path(self.project_dir).exists())
        result = _run(self.project_dir, extra_args=["--check"])
        self.assertEqual(result.returncode, 1, msg=f"stderr={result.stderr}")
        self.assertIn("GOLDEN MISSING", result.stderr)
        self.assertIn("--write-golden", result.stderr)

    def test_default_mode_does_not_touch_golden(self) -> None:
        """Without --check/--write-golden the golden gate is OFF (default-OFF).

        Legacy live cross-check still runs and passes, and no golden file
        is created as a side effect.
        """
        _write_audit_emit(self.project_dir, ["alpha", "beta"])
        _write_schema(self.project_dir, ["alpha", "beta"])
        _write_caller(
            self.project_dir,
            ".claude/scripts/c.py",
            "from _lib import audit_emit\n"
            "audit_emit.emit_alpha(x=1)\n",
        )
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 0, msg=f"stderr={result.stderr}")
        self.assertIn("audit registry in sync", result.stdout)
        # Default mode must NOT create the golden.
        self.assertFalse(_golden_path(self.project_dir).exists())

    def test_check_internal_error_when_audit_emit_missing(self) -> None:
        """--check with no audit_emit.py → exit 2 (internal error)."""
        _write_schema(self.project_dir, ["x"])  # only schema, no audit_emit
        result = _run(self.project_dir, extra_args=["--check"])
        self.assertEqual(result.returncode, 2, msg=f"stderr={result.stderr}")
        self.assertIn("audit_emit.py not found", result.stderr)

    def test_check_and_write_golden_mutually_exclusive(self) -> None:
        """--check + --write-golden together → argparse error (exit 2)."""
        _write_audit_emit(self.project_dir, ["alpha"])
        _write_schema(self.project_dir, ["alpha"])
        result = _run(
            self.project_dir, extra_args=["--check", "--write-golden"]
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with argument", result.stderr)

    def test_unregistered_def_excluded_from_golden(self) -> None:
        """A ``def emit_X`` whose X is NOT registered never enters the golden.

        ``_write_audit_emit`` with ``emit_defs_extra`` writes a def for an
        unregistered name; that def must NOT appear in the golden inventory
        (the live cross-check fails on it separately).
        """
        _write_audit_emit(
            self.project_dir, ["alpha"], emit_defs_extra=["ghostdef"]
        )
        _write_schema(self.project_dir, ["alpha"])
        # Write the golden directly; it is built from _KNOWN_ACTIONS only.
        _run(self.project_dir, extra_args=["--write-golden"])
        body = [
            ln
            for ln in _golden_path(self.project_dir)
            .read_text(encoding="utf-8")
            .splitlines()
            if not ln.startswith("#")
        ]
        self.assertEqual(body, ["alpha"])
        self.assertNotIn("ghostdef", body)


class TestRealRepoSmoke(unittest.TestCase):
    """Positive smoke test — the real repo's audit registry must pass.

    Skipped in environments that set ``CEO_SKIP_REAL_REGISTRY_SMOKE=1``;
    CI never sets that flag (per PLAN-013 Phase A.6 contract).
    """

    def test_real_repo_exit_0(self) -> None:
        if os.environ.get("CEO_SKIP_REAL_REGISTRY_SMOKE") == "1":
            self.skipTest("CEO_SKIP_REAL_REGISTRY_SMOKE=1 set")
        cmd = [sys.executable, str(SCRIPT), "--verbose"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"Real repo registry check MUST pass but exited "
                f"{result.returncode}.\nstdout={result.stdout}\n"
                f"stderr={result.stderr}"
            ),
        )

    def test_real_repo_golden_in_sync(self) -> None:
        """PLAN-133 E8 — the checked-in golden MUST match the live registry.

        This is the same assertion the new validate.yml ``--check`` step
        runs; a failing test here means ``--write-golden`` was not run in
        the commit that changed ``_KNOWN_ACTIONS``.
        """
        if os.environ.get("CEO_SKIP_REAL_REGISTRY_SMOKE") == "1":
            self.skipTest("CEO_SKIP_REAL_REGISTRY_SMOKE=1 set")
        cmd = [sys.executable, str(SCRIPT), "--check", "--verbose"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"Real repo golden check MUST pass but exited "
                f"{result.returncode}. Run --write-golden + commit.\n"
                f"stdout={result.stdout}\nstderr={result.stderr}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
