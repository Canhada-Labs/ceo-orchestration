"""PLAN-119-FOLLOWUP WS-2 — unit tests for the ``_lib.audit_emit`` shadow-loader
restore gate in ``.claude/scripts/check-test-audit-isolation.py``.

The gate flags any test file that INSTALLS a ``_lib.audit_emit`` shadow into the
canonical import slot without a TEARDOWN-scoped canonical restore — the
cross-suite leak that reddened CI on ``19ab91d``. These tests pin the
true-positives (incl. the evasions Codex `019e73ab` + the S184 adversarial-verify
P0 surfaced: module-top consumer-import masking, variable-key install,
update/setdefault install, incidental unrelated save/restore) AND the
true-negatives (re-import in tearDown, save-and-restore via addCleanup,
import_module via a module-constant, mock.patch.dict, no-install consumer) so the
gate cannot drift into a false-green machine.
"""
from __future__ import annotations

import contextlib
import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402  (env-isolated base per WS-A hygiene gate)

_GATE_PATH = REPO_ROOT / ".claude" / "scripts" / "check-test-audit-isolation.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("_ws2_gate_under_test", _GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


GATE = _load_gate()


def _flagged(src: str) -> bool:
    """Write ``src`` to a temp ``test_*.py`` and report whether the shadow gate flags it."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "test_probe.py"
        p.write_text(textwrap.dedent(src), encoding="utf-8")
        return any("`_lib.audit_emit` shadow" in msg for _ln, msg in GATE.check_file(p))


# --- TRUE-POSITIVES (a real un-restored shadow loader MUST be flagged) ----------

BAD_LITERAL_POP_ONLY = '''
    import sys, importlib.util
    def _load():
        spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_lib.audit_emit"] = mod
        return mod
    class T:
        def setUp(self):
            self.m = _load()
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)   # pop-only — the 19ab91d bug
'''

BAD_WITH_MODULE_TOP_CONSUMER_IMPORT = '''
    import sys, importlib.util
    from _lib import audit_emit   # module-top CONSUMER import — must NOT count as restore
    class T:
        def setUp(self):
            spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
            sys.modules["_lib.audit_emit"] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)
'''

BAD_VARIABLE_KEY = '''
    import sys, importlib.util
    SLOT = "_lib.audit_emit"
    class T:
        def setUp(self):
            spec = importlib.util.spec_from_file_location(SLOT, "/staged")
            sys.modules[SLOT] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            sys.modules.pop(SLOT, None)
'''

BAD_UPDATE = '''
    import sys
    class T:
        def setUp(self):
            sys.modules.update({"_lib.audit_emit": object()})
        def tearDown(self):
            pass
'''

BAD_SETDEFAULT = '''
    import sys
    class T:
        def setUp(self):
            sys.modules.setdefault("_lib.audit_emit", object())
        def tearDown(self):
            pass
'''

BAD_UPDATE_ITEMS = '''
    import sys
    class T:
        def setUp(self):
            sys.modules.update([("_lib.audit_emit", object())])   # items-list form
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)
'''

BAD_UPDATE_KWARGS = '''
    import sys
    class T:
        def setUp(self):
            sys.modules.update(**{"_lib.audit_emit": object()})   # ** form
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)
'''

# The S184 adversarial-verify P0: install + pop-only teardown, but the file has an
# UNRELATED sys.modules.get + an UNRELATED variable-keyed restore loop for OTHER
# modules (slot NOT in any saved collection). The old module-wide heuristic passed
# this; the class+teardown+slot-scoped gate must flag it.
BAD_INCIDENTAL_UNRELATED_RESTORE = '''
    import sys, importlib.util
    class T:
        def setUp(self):
            self._saved = {}
            for m in ("_lib.federation", "_lib.policy"):   # NOT _lib.audit_emit
                self._saved[m] = sys.modules.get(m)
            spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
            sys.modules["_lib.audit_emit"] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            for m, saved in self._saved.items():           # restores OTHER modules only
                sys.modules[m] = saved
            sys.modules.pop("_lib.audit_emit", None)        # slot itself: pop-only
'''

# The Codex `019e73ab` R2 nested-P0: a SAFE restoring class and an UNSAFE
# pop-only class in the SAME file. The safe class must NOT cover the unsafe one —
# install must be bound to its OWN class.
BAD_MULTICLASS_COEXIST = '''
    import sys, importlib, importlib.util
    class Safe:
        def setUp(self):
            spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
            sys.modules["_lib.audit_emit"] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            importlib.import_module("_lib.audit_emit")
    class Bad:
        def setUp(self):
            sys.modules["_lib.audit_emit"] = object()
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)   # pop-only — MUST still be flagged
'''


# --- TRUE-NEGATIVES (legitimate restore patterns must NOT be flagged) -----------

GOOD_REIMPORT_TEARDOWN = '''
    import sys, importlib, importlib.util
    def _load():
        spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_lib.audit_emit"] = mod
        return mod
    class T:
        def setUp(self):
            self.m = _load()
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)
            importlib.import_module("_lib.audit_emit")     # canonical restore
'''

GOOD_FROM_IMPORT_TEARDOWN = '''
    import sys, importlib.util
    class T:
        def setUp(self):
            spec = importlib.util.spec_from_file_location("_lib.audit_emit", "/staged")
            sys.modules["_lib.audit_emit"] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            sys.modules.pop("_lib.audit_emit", None)
            from _lib import audit_emit   # canonical restore INSIDE teardown
'''

GOOD_IMPORT_MODULE_CONST = '''
    import sys, importlib, importlib.util
    _SLOT = "_lib.audit_emit"
    class T:
        def setUp(self):
            spec = importlib.util.spec_from_file_location(_SLOT, "/staged")
            sys.modules[_SLOT] = importlib.util.module_from_spec(spec)
        def tearDown(self):
            sys.modules.pop(_SLOT, None)
            importlib.import_module(_SLOT)   # restore via module-constant name
'''

# The test_federation pattern: save the slot in a tuple via sys.modules.get, install
# the stub, restore via a variable-keyed loop in an addCleanup target.
GOOD_SAVE_RESTORE_ADDCLEANUP = '''
    import sys, types
    class T:
        def setUp(self):
            self._saved = {}
            for m in ("_lib", "_lib.audit_emit", "_lib.federation"):
                self._saved[m] = sys.modules.get(m)
            sys.modules["_lib.audit_emit"] = types.ModuleType("stub")
            self.addCleanup(self._tidy)
        def _tidy(self):
            for m, saved in self._saved.items():
                sys.modules[m] = saved
'''

GOOD_PATCH_DICT = '''
    from unittest import mock
    class T:
        def test_x(self):
            with mock.patch.dict("sys.modules", {"_lib.audit_emit": object()}):
                pass
'''

GOOD_NO_INSTALL_CONSUMER = '''
    import sys
    from _lib import audit_emit
    class T:
        def test_x(self):
            if "_lib.audit_emit" in sys.modules:
                del sys.modules["_lib.audit_emit"]
            from _lib import audit_emit as ae
            assert ae is not None
'''


class TruePositiveTest(TestEnvContext):
    def test_literal_pop_only(self) -> None:
        self.assertTrue(_flagged(BAD_LITERAL_POP_ONLY))

    def test_module_top_consumer_import_does_not_mask(self) -> None:
        self.assertTrue(_flagged(BAD_WITH_MODULE_TOP_CONSUMER_IMPORT))

    def test_variable_key_install(self) -> None:
        self.assertTrue(_flagged(BAD_VARIABLE_KEY))

    def test_update_install(self) -> None:
        self.assertTrue(_flagged(BAD_UPDATE))

    def test_setdefault_install(self) -> None:
        self.assertTrue(_flagged(BAD_SETDEFAULT))

    def test_update_items_list_install(self) -> None:
        self.assertTrue(_flagged(BAD_UPDATE_ITEMS))

    def test_update_kwargs_install(self) -> None:
        self.assertTrue(_flagged(BAD_UPDATE_KWARGS))

    def test_incidental_unrelated_restore_does_not_mask(self) -> None:
        self.assertTrue(_flagged(BAD_INCIDENTAL_UNRELATED_RESTORE))

    def test_safe_class_does_not_cover_unsafe_sibling(self) -> None:
        self.assertTrue(_flagged(BAD_MULTICLASS_COEXIST))


class TrueNegativeTest(TestEnvContext):
    def test_reimport_teardown(self) -> None:
        self.assertFalse(_flagged(GOOD_REIMPORT_TEARDOWN))

    def test_from_import_teardown(self) -> None:
        self.assertFalse(_flagged(GOOD_FROM_IMPORT_TEARDOWN))

    def test_import_module_module_constant(self) -> None:
        self.assertFalse(_flagged(GOOD_IMPORT_MODULE_CONST))

    def test_save_restore_addcleanup(self) -> None:
        self.assertFalse(_flagged(GOOD_SAVE_RESTORE_ADDCLEANUP))

    def test_patch_dict_not_flagged(self) -> None:
        self.assertFalse(_flagged(GOOD_PATCH_DICT))

    def test_no_install_consumer_not_flagged(self) -> None:
        self.assertFalse(_flagged(GOOD_NO_INSTALL_CONSUMER))


class HelperPrecisionTest(TestEnvContext):
    def test_is_sys_modules_rejects_other_modules_attr(self) -> None:
        import ast
        tree = ast.parse("foo.modules[x] = y\n")
        # foo.modules is NOT sys.modules — _is_sys_modules must reject it
        attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
        self.assertTrue(any(a.attr == "modules" for a in attrs))
        self.assertFalse(any(GATE._is_sys_modules(a) for a in attrs))

    def test_slot_names_resolves_binding(self) -> None:
        import ast
        tree = ast.parse('SLOT = "_lib.audit_emit"\nOTHER = "x"\n')
        self.assertEqual(GATE._slot_names(tree), {"SLOT"})


class LiveCorpusTest(TestEnvContext):
    """The shipped gate must be GREEN against the live test corpus (HEAD). Pinned
    to REPO_ROOT so it is NOT CWD-dependent (the adversarial-verify flagged that a
    non-repo CWD made GATE.main scan zero files and pass vacuously)."""

    def test_gate_green_on_head(self) -> None:
        import io
        buf = io.StringIO()
        prev = os.getcwd()
        try:
            os.chdir(REPO_ROOT)
            with contextlib.redirect_stdout(buf):
                rc = GATE.main(["check-test-audit-isolation.py"])
        finally:
            os.chdir(prev)
        self.assertEqual(rc, 0, msg=buf.getvalue())


if __name__ == "__main__":
    unittest.main()
