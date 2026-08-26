#!/usr/bin/env python3
"""Census of the "patch on a STALE ``_lib.audit_emit`` object" hazard class.

THE CLASS (paid for in S329, PLAN-179 pack D)
---------------------------------------------
A test binds the emitter module at import time::

    from _lib import audit_emit          # module-level, in the TEST file
    ...
    mock.patch.object(audit_emit, "emit_x", fake)

while the code under test re-resolves it on every call::

    def _emit_rejection(...):
        from _lib import audit_emit      # call-time, in the PRODUCTION file
        typed = getattr(audit_emit, "emit_ledger_entry_rejected", None)

If any predecessor in the same pytest worker pops or rebinds
``_lib.audit_emit`` (many files in this suite do; the measured polluter is
``test_check_agent_spawn.py::TestPLAN078Wave1ModelRoutingAdvisory``, which
re-creates the module in ``tearDown``), the test file's module-level name goes
STALE. The patch then lands on an object nobody reads, the production code
calls the REAL emitter, and the assertion fails with ``len(calls) == 0`` - an
ORDER-dependent flake, green in isolation.

The asymmetry that makes this a class and not a one-off: when the CONSUMER
also binds at import time, consumer and test go stale TOGETHER onto the same
object, so the patch still lands. Only a call-time consumer re-resolves to a
fresh object while the test keeps the old one.

INVERTED CLASSIFICATION RULE (PLAN-185 anti-pattern 6)
------------------------------------------------------
Forms are not "safe because no rule matched". This instrument enumerates the
forms it can PROVE safe; everything else is ``INDETERMINADO``. A verdict of
``SEGURO`` is an affirmative claim with a printed criterion, never a default.

EXIT CODES
----------
    0  census completed; no INDETERMINADO site (or --strict not given)
    1  --strict and at least one INDETERMINADO site
    2  usage error / no test root found
    3  internal parse failure that would silently shrink the census

ADVISORY. This script gates nothing; it produces the census a cure wave
consumes. It is NOT a member of the ADR-192 gate-scripts manifest.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# The emitter module this census is about.
# --------------------------------------------------------------------------
EMITTER_MODULE = "audit_emit"
EMITTER_DOTTED = "_lib.audit_emit"

# Verdicts.
V_FRAGIL = "FRAGIL"
V_SEGURO = "SEGURO"
V_LOOKUP_VIVO = "LOOKUP-VIVO"
V_INDETERMINADO = "INDETERMINADO"

# Target-module emitter-resolution kinds.
R_CALL_TIME = "call-time"
R_IMPORT_TIME_MODULE = "import-time-module"
R_IMPORT_TIME_FUNCTION = "import-time-function"
R_NONE = "none"
R_INDETERMINATE = "indeterminado"

# Patch-site forms.
F_OBJ_ALIAS = "obj-alias"          # patch.object(<audit_emit alias>, "attr")
F_OBJ_LIVE = "obj-live-lookup"     # patch.object(_live_audit_emit(), "attr")
F_OBJ_CONSUMER = "obj-consumer"    # patch.object(<module under test>, "_audit_emit")
F_STRING = "string-target"         # patch("_lib.audit_emit.attr")
F_REBIND = "live-rebind"           # alias = reload(import_module(...))
F_UNMODELLED = "unmodelled-form"   # patch-shaped, mentions the emitter,
                                   # matched no modelled rule
F_ASSIGN = "direct-assign"         # <alias>.emit_x = fake
F_RELOAD = "reload-stale"          # importlib.reload(<alias>)


def _dotted(node):
    """Render ``a.b.c`` from an Attribute/Name chain, else None."""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _is_emitter_import(node):
    """True when `node` binds the audit_emit MODULE object.

    Modelled forms (and ONLY these):
      * ``from _lib import audit_emit [as X]``      (ImportFrom)
      * ``import _lib.audit_emit as X``             (Import with asname)
    """
    if isinstance(node, ast.ImportFrom):
        base = node.module or ""
        if base == "_lib" or base.endswith("._lib") or base == "":
            return any(a.name == EMITTER_MODULE for a in node.names)
        return False
    if isinstance(node, ast.Import):
        return any(
            a.name == EMITTER_DOTTED or a.name.endswith("." + EMITTER_DOTTED)
            for a in node.names
        )
    return False


def _emitter_aliases(node):
    """Local names bound to the audit_emit MODULE by `node`."""
    out = set()
    if isinstance(node, ast.ImportFrom):
        base = node.module or ""
        if base == "_lib" or base.endswith("._lib") or base == "":
            for a in node.names:
                if a.name == EMITTER_MODULE:
                    out.add(a.asname or a.name)
    elif isinstance(node, ast.Import):
        for a in node.names:
            if a.name == EMITTER_DOTTED or a.name.endswith("." + EMITTER_DOTTED):
                if a.asname:
                    out.add(a.asname)
                # `import _lib.audit_emit` with no asname binds `_lib`, the
                # PACKAGE, not the emitter module - deliberately not an alias.
    return out


# --------------------------------------------------------------------------
# Part 1 - classify how a module UNDER TEST resolves the emitter.
# --------------------------------------------------------------------------

class TargetClassifier(ast.NodeVisitor):
    """Derive a module's emitter-resolution kind from its AST."""

    def __init__(self):
        self.call_time_functions = []
        self.module_level_module_aliases = set()
        self.module_level_function_imports = set()
        self.unmodelled = []
        self._fn_stack = []

    def _enter_fn(self, node):
        self._fn_stack.append(node.name)
        self.generic_visit(node)
        self._fn_stack.pop()

    def visit_FunctionDef(self, node):
        self._enter_fn(node)

    def visit_AsyncFunctionDef(self, node):
        self._enter_fn(node)

    def visit_ImportFrom(self, node):
        if _is_emitter_import(node) and self._fn_stack:
            self.call_time_functions.append((self._fn_stack[-1], node.lineno))
        self.generic_visit(node)

    def visit_Import(self, node):
        if _is_emitter_import(node) and self._fn_stack:
            self.call_time_functions.append((self._fn_stack[-1], node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node):
        d = _dotted(node.func) or ""
        if d.endswith("import_module") or d == "__import__":
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    if EMITTER_MODULE in a.value:
                        if self._fn_stack:
                            self.call_time_functions.append(
                                (self._fn_stack[-1], node.lineno)
                            )
                        else:
                            self.unmodelled.append(
                                ("module-level import_module", node.lineno)
                            )
        self.generic_visit(node)

    def visit_Subscript(self, node):
        d = _dotted(node.value) or ""
        if d.endswith("sys.modules") or d == "modules":
            sl = node.slice
            key = sl.value if isinstance(sl, ast.Index) else sl
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if EMITTER_MODULE in key.value:
                    if self._fn_stack:
                        self.call_time_functions.append(
                            (self._fn_stack[-1], node.lineno)
                        )
                    else:
                        self.unmodelled.append(
                            ("module-level sys.modules lookup", node.lineno)
                        )
        self.generic_visit(node)


def classify_target(path):
    """Return {kind, evidence, aliases} for one module under test."""
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return {
            "kind": R_INDETERMINATE,
            "evidence": "unparseable: {0}".format(exc.__class__.__name__),
            "aliases": [],
        }

    c = TargetClassifier()
    for node in tree.body:
        if _is_emitter_import(node):
            c.module_level_module_aliases |= _emitter_aliases(node)
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(
            EMITTER_DOTTED
        ):
            for a in node.names:
                c.module_level_function_imports.add(a.asname or a.name)
        if isinstance(node, ast.Try):
            for sub in ast.walk(node):
                if _is_emitter_import(sub):
                    c.module_level_module_aliases |= _emitter_aliases(sub)
                if isinstance(sub, ast.ImportFrom) and (
                    sub.module or ""
                ).endswith(EMITTER_DOTTED):
                    for a in sub.names:
                        c.module_level_function_imports.add(a.asname or a.name)
    c.visit(tree)

    if c.call_time_functions:
        ev = "; ".join(
            "{0}() @L{1}".format(fn, ln) for fn, ln in c.call_time_functions[:4]
        )
        return {
            "kind": R_CALL_TIME,
            "evidence": "fresh resolution inside function body: " + ev,
            "aliases": sorted(c.module_level_module_aliases),
        }
    if c.unmodelled:
        ev = "; ".join("{0} @L{1}".format(w, ln) for w, ln in c.unmodelled[:4])
        return {"kind": R_INDETERMINATE, "evidence": ev, "aliases": []}
    if c.module_level_module_aliases:
        return {
            "kind": R_IMPORT_TIME_MODULE,
            "evidence": "module-level module binding: {0}".format(
                ", ".join(sorted(c.module_level_module_aliases))
            ),
            "aliases": sorted(c.module_level_module_aliases),
        }
    if c.module_level_function_imports:
        return {
            "kind": R_IMPORT_TIME_FUNCTION,
            "evidence": "module-level FUNCTION binding: {0}".format(
                ", ".join(sorted(c.module_level_function_imports))
            ),
            "aliases": [],
        }
    return {"kind": R_NONE, "evidence": "no audit_emit reference", "aliases": []}


def build_target_index(hook_dirs):
    """module stem -> classification, for every module under test."""
    index = {}
    for d in hook_dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            if p.name == "__init__.py":
                continue
            info = classify_target(p)
            info["path"] = str(p)
            index[p.stem] = info
    return index


# --------------------------------------------------------------------------
# Part 2 - find the patch sites in one TEST file.
# --------------------------------------------------------------------------

class TestFileScanner(ast.NodeVisitor):
    """Collect emitter aliases, live-lookup providers, and patch sites."""

    def __init__(self, path):
        self.path = path
        self.module_aliases = set()      # stale-able (module scope)
        self.local_aliases = set()       # bound INSIDE a function
        self.live_providers = set()      # helpers returning a live lookup
        self.imported_modules = set()    # candidate targets
        self.sites = []
        self.live_rebinds = []
        self._fn_stack = []

    def _enter_fn(self, node):
        self._fn_stack.append(node.name)
        self.generic_visit(node)
        self._fn_stack.pop()

    @staticmethod
    def _returns_one_of(fn_node, names):
        """True when the function RETURNS something built from `names`."""
        for sub in ast.walk(fn_node):
            if isinstance(sub, ast.Return) and sub.value is not None:
                try:
                    src = ast.unparse(sub.value)
                except Exception:
                    continue
                for n in names:
                    if n == src:
                        return True
                    probes = (n + ".", "(" + n, ", " + n, "(" + n + ",",
                              " " + n + ")", " " + n + ",")
                    for probe in probes:
                        if probe in src:
                            return True
        return False

    def visit_FunctionDef(self, node):
        self._enter_fn(node)

    def visit_AsyncFunctionDef(self, node):
        self._enter_fn(node)

    def _record_import(self, node):
        aliases = _emitter_aliases(node)
        if aliases:
            if self._fn_stack:
                self.local_aliases |= aliases
            else:
                self.module_aliases |= aliases
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != EMITTER_MODULE:
                    self.imported_modules.add(a.asname or a.name)
                    self.imported_modules.add(a.name)
            if node.module:
                self.imported_modules.add(node.module.split(".")[-1])
        else:
            for a in node.names:
                self.imported_modules.add(a.name.split(".")[-1])
                if a.asname:
                    self.imported_modules.add(a.asname)

    def visit_ImportFrom(self, node):
        self._record_import(node)
        self.generic_visit(node)

    def visit_Import(self, node):
        self._record_import(node)
        self.generic_visit(node)

    def visit_Call(self, node):
        d = _dotted(node.func) or ""
        tail = d.split(".")[-1]
        prev = d.split(".")[-2] if "." in d else ""

        is_patch_object = tail == "object" and prev == "patch"
        is_patch_str = tail == "patch"
        is_setattr = tail == "setattr"

        # importlib.reload(<alias>) is a SITE of the same class: reload
        # asserts `sys.modules[mod.__name__] is mod`, so a stale object
        # raises ImportError outright. Independent of the consumer.
        if tail == "reload" and node.args:
            try:
                rsrc = ast.unparse(node.args[0])
            except Exception:
                rsrc = "<unparseable>"
            rhead = rsrc.split(".")[0].split("(")[0].strip()
            if rhead in self.module_aliases:
                self._add_site(node, F_RELOAD, rsrc, None)
            elif rhead in self.local_aliases or rhead in self.live_providers:
                self._add_site(node, F_OBJ_LIVE, rsrc, None)

        if (is_patch_object or is_patch_str or is_setattr) and node.args:
            a0 = node.args[0]
            attr = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                if isinstance(node.args[1].value, str):
                    attr = node.args[1].value

            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                if EMITTER_MODULE in a0.value:
                    self._add_site(node, F_STRING, a0.value, None)
            else:
                try:
                    src = ast.unparse(a0)
                except Exception:
                    src = "<unparseable>"
                head = src.split(".")[0].split("(")[0].strip()
                if head in self.live_providers:
                    self._add_site(node, F_OBJ_LIVE, src, attr)
                elif head in self.local_aliases and head not in self.module_aliases:
                    self._add_site(node, F_OBJ_LIVE, src, attr)
                elif head in self.module_aliases:
                    self._add_site(node, F_OBJ_ALIAS, src, attr)
                elif attr is not None and EMITTER_MODULE in attr:
                    self._add_site(node, F_OBJ_CONSUMER, src, attr)
                elif isinstance(a0, ast.Attribute) and EMITTER_MODULE in a0.attr:
                    # patch.object(<module under test>._audit_emit, "emit_x"):
                    # the target OBJECT is the consumer's own alias, resolved
                    # by attribute lookup at patch time.
                    self._add_site(node, F_OBJ_CONSUMER, src, attr)
                elif EMITTER_MODULE in src:
                    # Patch-shaped, mentions the emitter, matched no modelled
                    # rule. The INVERTED rule forbids dropping it silently.
                    self._add_site(node, F_UNMODELLED, src, attr)
        self.generic_visit(node)

    def visit_Assign(self, node):
        # `audit_emit = importlib.reload(importlib.import_module(...))` in a
        # setUp REBINDS the module-level global to a fresh object before each
        # test, so every later use of the name is live. Precedent already in
        # the tree: test_spool_drain_rotation_race.py setUp.
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in self.module_aliases:
                try:
                    vsrc = ast.unparse(node.value)
                except Exception:
                    vsrc = ""
                live = ("import_module" in vsrc and EMITTER_MODULE in vsrc) or (
                    "__import__" in vsrc and EMITTER_MODULE in vsrc
                )
                if live:
                    fn = self._fn_stack[-1] if self._fn_stack else "<module>"
                    self.live_rebinds.append((fn, node.lineno))
                    # Surface the CURE as a site so the census shows where it
                    # lives (and so the anti-drop cross-check stays honest).
                    self._add_site(node, F_REBIND, t.id, None)
        for t in node.targets:
            if isinstance(t, ast.Attribute):
                d = _dotted(t) or ""
                head = d.split(".")[0]
                base = d.rsplit(".", 1)[0] if "." in d else d
                if head in self.module_aliases:
                    self._add_site(node, F_ASSIGN, base, t.attr)
                elif head in self.local_aliases:
                    self._add_site(node, F_OBJ_LIVE, base, t.attr)
        self.generic_visit(node)

    def _add_site(self, node, form, target, attr):
        self.sites.append(
            {
                "file": self.path,
                "line": node.lineno,
                "form": form,
                "target_expr": target,
                "attr": attr,
                "enclosing": self._fn_stack[-1] if self._fn_stack else "<module>",
            }
        )


# --------------------------------------------------------------------------
# Part 3 - verdict per site.
# --------------------------------------------------------------------------

def infer_targets(scanner, index, stem):
    """Modules under test this file plausibly exercises.

    Criterion (printed in the report): the union of
      (a) every name the test file imports that is a known module under test,
      (b) the filename heuristic ``test_<stem>.py`` -> ``<stem>``,
    minus the emitter module itself and pure test helpers.
    """
    out = set()
    for name in scanner.imported_modules:
        if name in index and name != EMITTER_MODULE:
            out.add(name)
    base = stem[len("test_"):] if stem.startswith("test_") else stem
    if base in index:
        out.add(base)
    out.discard("testing")
    out.discard("test_isolation")
    return sorted(out)


SETUP_FUNCS = ("setUp", "setUpClass", "setup_method", "setup_class")


def verdict_for_site(site, targets, index, live_rebinds=()):
    """(verdict, criterion). INVERTED rule: prove safe, else INDETERMINADO."""
    form = site["form"]

    # A per-test live rebind of the module-level alias makes every later use
    # of that name live. Only a setUp-like rebind runs before EVERY test.
    setup_rebind = [ln for fn, ln in live_rebinds if fn in SETUP_FUNCS]
    if setup_rebind and form in (F_OBJ_ALIAS, F_ASSIGN, F_RELOAD):
        return (
            V_LOOKUP_VIVO,
            "the module-level alias is REBOUND from a live import in setUp "
            "(L{0}), so it is fresh for every test. CAVEAT: this holds only "
            "while that setUp runs before the site".format(setup_rebind[0]),
        )

    if form == F_REBIND:
        return (
            V_LOOKUP_VIVO,
            "this IS the cure: the module-level alias is reassigned from a "
            "live import, so later uses of the name are fresh",
        )

    if form == F_OBJ_LIVE:
        return (
            V_LOOKUP_VIVO,
            "patch target is resolved by a LIVE lookup at patch time "
            "(same IMPORT_FROM semantics the consumer uses)",
        )

    if form == F_OBJ_CONSUMER:
        return (
            V_SEGURO,
            "patch lands on an attribute of the module UNDER TEST, not on "
            "_lib.audit_emit - immune to pop/rebind of the emitter module",
        )

    if form == F_STRING:
        return (
            V_INDETERMINADO,
            "string target re-resolves at patch time via mock._dot_lookup "
            "(getattr on the _lib package, NO sys.modules fallback): immune "
            "to the stale-rebind variant, but RAISES AttributeError under the "
            "dangling-package-attribute variant. Not provably safe",
        )

    if form == F_RELOAD:
        return (
            V_FRAGIL,
            "importlib.reload() on a module-level alias: reload asserts "
            "sys.modules[name] is the SAME object, so any predecessor "
            "pop/rebind makes this raise ImportError - fragile regardless of "
            "how the consumer resolves the emitter",
        )

    if form in (F_OBJ_ALIAS, F_ASSIGN):
        if not targets:
            return (
                V_INDETERMINADO,
                "no module under test could be inferred, so the consumer's "
                "resolution kind is unknown",
            )
        kinds = {}
        for t in targets:
            kinds[t] = index[t]["kind"]
        call_time = [t for t, k in kinds.items() if k == R_CALL_TIME]
        if EMITTER_MODULE in kinds and not call_time:
            # The module under test IS the emitter. The test patches the
            # subject through the same module-level name it later calls
            # through, so patch target and consumer are the SAME object by
            # construction - they go stale together or not at all.
            return (
                V_SEGURO,
                "the module under test IS audit_emit: the patch target and "
                "the consumer are the same module-level name in the same "
                "file, so a rebind moves both together",
            )
        if call_time:
            return (
                V_FRAGIL,
                "module-level alias is stale-able AND inferred target(s) "
                "{0} re-resolve the emitter at CALL time".format(
                    ", ".join(sorted(call_time))
                ),
            )
        indet = [t for t, k in kinds.items() if k == R_INDETERMINATE]
        if indet:
            return (
                V_INDETERMINADO,
                "inferred target(s) {0} resolve the emitter in a form this "
                "parser does not model".format(", ".join(sorted(indet))),
            )
        fnkind = [t for t, k in kinds.items() if k == R_IMPORT_TIME_FUNCTION]
        if fnkind:
            return (
                V_INDETERMINADO,
                "inferred target(s) {0} bind the emitter FUNCTION directly at "
                "import time; a patch on the module object never reaches "
                "them".format(", ".join(sorted(fnkind))),
            )
        modkind = [t for t, k in kinds.items() if k == R_IMPORT_TIME_MODULE]
        if modkind:
            return (
                V_SEGURO,
                "inferred target(s) {0} bind the emitter module at IMPORT "
                "time: consumer and test go stale onto the SAME object, so "
                "the patch still lands".format(", ".join(sorted(modkind))),
            )
        return (
            V_INDETERMINADO,
            "inferred target(s) never reference audit_emit; the patch has no "
            "provable consumer",
        )

    if form == F_UNMODELLED:
        return (
            V_INDETERMINADO,
            "patch-shaped call naming the emitter that matched no modelled "
            "form; classified INDETERMINADO rather than dropped",
        )

    return (V_INDETERMINADO, "unmodelled patch form")


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def find_repo_root(start):
    for parent in [start] + list(start.parents):
        if (parent / ".claude" / "hooks" / "_lib" / "__init__.py").is_file():
            return parent
    return None


def run_census(root):
    test_dirs = [
        root / ".claude" / "hooks" / "tests",
        root / ".claude" / "hooks" / "_lib" / "tests",
    ]
    hook_dirs = [
        root / ".claude" / "hooks",
        root / ".claude" / "hooks" / "_lib",
    ]
    index = build_target_index(hook_dirs)

    scanned = []
    parse_failures = []
    results = []

    for d in test_dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("test_*.py")):
            rel = str(p.relative_to(root))
            scanned.append(rel)
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                parse_failures.append("{0}: {1}".format(rel, exc))
                continue
            sc = TestFileScanner(rel)
            # Module-level emitter bindings must be known BEFORE sites are
            # judged, so they are collected in a pre-pass.
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    sc.module_aliases |= _emitter_aliases(node)
                if isinstance(node, ast.Try):
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            sc.module_aliases |= _emitter_aliases(sub)
            # Pre-pass: discover live-lookup providers.
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    binds = set()
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            binds |= _emitter_aliases(sub)
                    if binds:
                        sc.local_aliases |= binds
                        if TestFileScanner._returns_one_of(node, binds):
                            sc.live_providers.add(node.name)
            sc.visit(tree)
            if not sc.sites:
                continue
            targets = infer_targets(sc, index, p.stem)
            for site in sc.sites:
                v, crit = verdict_for_site(
                    site, targets, index, sc.live_rebinds
                )
                site["verdict"] = v
                site["criterion"] = crit
                site["inferred_targets"] = targets
                site["target_kinds"] = dict(
                    (t, index[t]["kind"]) for t in targets
                )
                results.append(site)

    return {
        "root": str(root),
        "test_dirs": [str(d) for d in test_dirs],
        "files_scanned": len(scanned),
        "target_modules_indexed": len(index),
        "parse_failures": parse_failures,
        "sites": results,
        "target_index": dict(
            (k, {"kind": v["kind"], "evidence": v["evidence"],
                 "path": v["path"]})
            for k, v in index.items()
            if v["kind"] != R_NONE
        ),
    }


def render_text(census, out):
    sites = census["sites"]
    w = out.write

    w("=" * 74 + "\n")
    w("STALE-MODULE-PATCH CENSUS - _lib.audit_emit\n")
    w("=" * 74 + "\n\n")

    w("INPUTS (a measurement prints its inputs)\n")
    w("  repo root ............. {0}\n".format(census["root"]))
    for d in census["test_dirs"]:
        w("  test dir .............. {0}\n".format(d))
    w("  test files scanned .... {0}\n".format(census["files_scanned"]))
    w("  target modules indexed  {0}\n".format(census["target_modules_indexed"]))
    w("  parse failures ........ {0}\n".format(len(census["parse_failures"])))
    for pf in census["parse_failures"]:
        w("      ! {0}\n".format(pf))
    w("\n")

    ti = census["target_index"]
    by_kind = {}
    for name, info in ti.items():
        by_kind.setdefault(info["kind"], []).append(name)
    w("TARGET MODULES BY EMITTER RESOLUTION (the consumer side)\n")
    for kind in (R_CALL_TIME, R_IMPORT_TIME_MODULE, R_IMPORT_TIME_FUNCTION,
                 R_INDETERMINATE):
        names = sorted(by_kind.get(kind, []))
        shown = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
        w("  {0:<22} {1:>3}  {2}\n".format(kind, len(names), shown))
    w("\n")

    forms = {}
    verdicts = {}
    for s in sites:
        forms[s["form"]] = forms.get(s["form"], 0) + 1
        verdicts[s["verdict"]] = verdicts.get(s["verdict"], 0) + 1

    w("PATCH SITES BY FORM\n")
    for k in sorted(forms):
        w("  {0:<18} {1:>3}\n".format(k, forms[k]))
    w("\nVERDICTS\n")
    for k in (V_FRAGIL, V_INDETERMINADO, V_SEGURO, V_LOOKUP_VIVO):
        w("  {0:<18} {1:>3}\n".format(k, verdicts.get(k, 0)))
    w("\n")

    by_file = {}
    for s in sites:
        by_file.setdefault(s["file"], []).append(s)

    order = {V_FRAGIL: 0, V_INDETERMINADO: 1, V_SEGURO: 2, V_LOOKUP_VIVO: 3}
    w("SITES\n")
    for f in sorted(by_file):
        fs = by_file[f]
        worst = min(order.get(s["verdict"], 9) for s in fs)
        tag = [k for k, v in order.items() if v == worst][0]
        w("\n  {0}  [worst={1}]\n".format(f, tag))
        tg = fs[0].get("inferred_targets") or []
        w("      inferred targets: {0}\n".format(", ".join(tg) or "(none)"))
        for s in sorted(fs, key=lambda x: x["line"]):
            label = (s["target_expr"] or "")
            if s["attr"]:
                label = label + "." + s["attr"]
            w("      L{0:<5} {1:<14} {2:<16} {3}\n".format(
                s["line"], s["verdict"], s["form"], label))
            w("             why: {0}\n".format(s["criterion"]))
    w("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="check-stale-module-patch.py",
        description=(
            "Census of patch sites that may land on a STALE _lib.audit_emit "
            "object. ADVISORY - gates nothing."
        ),
        epilog=(
            "EXIT CODES: 0 = census ok; 1 = --strict and >=1 INDETERMINADO; "
            "2 = usage error / no repo root; 3 = parse failure that would "
            "silently shrink the census."
        ),
    )
    ap.add_argument("--root", default=None, help="repo root (default: derive)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when any site is INDETERMINADO",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.root:
        root = Path(args.root).resolve()
    else:
        env = os.environ.get("CLAUDE_PROJECT_DIR")
        start = Path(env).resolve() if env else Path(__file__).resolve().parent
        found = find_repo_root(start)
        if found is None:
            found = find_repo_root(Path.cwd().resolve())
        if found is None:
            sys.stderr.write("error: could not locate repo root\n")
            return 2
        root = found

    if not (root / ".claude" / "hooks").is_dir():
        sys.stderr.write("error: no .claude/hooks under {0}\n".format(root))
        return 2

    census = run_census(root)

    if args.json:
        json.dump(census, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        render_text(census, sys.stdout)

    if census["parse_failures"]:
        return 3
    if args.strict:
        for s in census["sites"]:
            if s["verdict"] == V_INDETERMINADO:
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
