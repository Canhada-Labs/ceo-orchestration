#!/usr/bin/env python3
"""Tests for ``check-stale-module-patch.py`` (PLAN-179, night-run S329 U2).

Every tree is built under ``tmp_path`` and the script is driven through its
``--root`` flag, so ``$HOME`` / ``$CLAUDE_PROJECT_DIR`` are never read or
written (env-hygiene gate). No ``os.environ`` mutation anywhere in this file.

POSITIVE-CONTROL DISCIPLINE
---------------------------
The controls below reproduce the MECHANISM the instrument claims to detect -
a real call-time ``from _lib import audit_emit`` in the AST of the module
under test - not merely its appearance. The strongest control is
``test_s329_incident_shape_*``: it replays the exact pre-cure and post-cure
shapes of ``test_ledger_provenance.py``, the flake that aborted the S328 land
of pack D, and asserts the verdict FLIPS between them.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _SCRIPTS_DIR / "check-stale-module-patch.py"


def _load_module():
    """Import the hyphenated script by file path."""
    spec = importlib.util.spec_from_file_location(
        "check_stale_module_patch", str(_SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _shadow(root: Path, targets: dict, tests: dict) -> Path:
    """Build a minimal shadow repo: hooks package + test dir.

    ``targets`` maps ``"<name>.py"`` -> module source (placed in
    ``.claude/hooks/_lib/``); ``tests`` maps ``"test_<name>.py"`` -> test
    source (placed in ``.claude/hooks/tests/``).
    """
    _write(root, ".claude/hooks/_lib/__init__.py", "")
    for name, body in targets.items():
        _write(root, ".claude/hooks/_lib/" + name, body)
    for name, body in tests.items():
        _write(root, ".claude/hooks/tests/" + name, body)
    return root


def _census(root: Path) -> dict:
    mod = _load_module()
    return mod.run_census(root)


def _sites(root: Path) -> list:
    return _census(root)["sites"]


def _verdicts(root: Path) -> list:
    return [s["verdict"] for s in _sites(root)]


def _run_cli(root: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--root", str(root)] + list(extra),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Source fragments. Assembled at runtime so this file holds no importable
# module-level `from _lib import audit_emit` of its own.
# ---------------------------------------------------------------------------

CALL_TIME_TARGET = '''\
"""A consumer that re-resolves the emitter on EVERY call."""


def emit_rejection(reason):
    from _lib import audit_emit          # call-time resolution

    fn = getattr(audit_emit, "emit_generic", None)
    if fn is not None:
        fn(action="rejected", reason=reason)
'''

IMPORT_TIME_TARGET = '''\
"""A consumer that binds the emitter module ONCE, at import time."""

from _lib import audit_emit              # import-time module binding


def emit_rejection(reason):
    audit_emit.emit_generic(action="rejected", reason=reason)
'''

TEST_PATCHES_TOP_OBJECT = '''\
from __future__ import annotations

import unittest.mock as mock

from _lib import audit_emit              # module-level: STALE-able
from _lib import subject


def test_emits():
    with mock.patch.object(audit_emit, "emit_generic") as fake:
        subject.emit_rejection("x")
    assert fake.call_count == 1
'''

TEST_LIVE_LOOKUP = '''\
from __future__ import annotations

import unittest.mock as mock

from _lib import audit_emit              # module-level, but NOT the patch target
from _lib import subject


def _live_audit_emit():
    """Resolve the object the consumer will ACTUALLY read, right now."""
    from _lib import audit_emit as _ae
    return _ae


def test_emits():
    with mock.patch.object(_live_audit_emit(), "emit_generic") as fake:
        subject.emit_rejection("x")
    assert fake.call_count == 1
'''

TEST_UNMODELLED_FORM = '''\
from __future__ import annotations

import unittest.mock as mock

from _lib import audit_emit


def test_emits():
    with mock.patch("_lib.audit_emit.emit_generic") as fake:
        assert fake is not None
'''


# ---------------------------------------------------------------------------
# (i) call-time target + patch on the module-level object  =>  FRAGIL
# ---------------------------------------------------------------------------
def test_call_time_target_with_top_object_patch_is_fragil(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    s = sites[0]
    assert s["verdict"] == "FRAGIL", s
    assert s["form"] == "obj-alias"
    assert "subject" in s["criterion"]
    assert "CALL time" in s["criterion"]


def test_fragil_site_names_path_and_line(tmp_path: Path) -> None:
    """A finding must be actionable: it names file AND line."""
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    s = _sites(root)[0]
    assert s["file"].endswith("test_subject.py")
    expected_line = TEST_PATCHES_TOP_OBJECT.splitlines().index(
        "    with mock.patch.object(audit_emit, \"emit_generic\") as fake:"
    ) + 1
    assert s["line"] == expected_line, (s["line"], expected_line)


def test_call_time_detection_is_structural_not_textual(tmp_path: Path) -> None:
    """The classifier must read the AST, not the word 'call-time'.

    Same target, but the fresh import is moved to module scope. The verdict
    must change even though the file still mentions audit_emit identically.
    """
    moved = CALL_TIME_TARGET.replace(
        "def emit_rejection(reason):\n    from _lib import audit_emit",
        "from _lib import audit_emit\n\n\ndef emit_rejection(reason):",
    )
    root = _shadow(
        tmp_path,
        {"subject.py": moved},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    assert _verdicts(root) == ["SEGURO"], _sites(root)


# ---------------------------------------------------------------------------
# (ii) live lookup  =>  LOOKUP-VIVO
# ---------------------------------------------------------------------------
def test_live_lookup_variant_is_lookup_vivo(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_LIVE_LOOKUP},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "LOOKUP-VIVO", sites[0]
    assert sites[0]["form"] == "obj-live-lookup"


# ---------------------------------------------------------------------------
# (iii) import-time target + coherent patch  =>  SEGURO
# ---------------------------------------------------------------------------
def test_import_time_target_with_object_patch_is_seguro(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": IMPORT_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "SEGURO", sites[0]
    assert "IMPORT" in sites[0]["criterion"]


# ---------------------------------------------------------------------------
# (iv) unmodelled form  =>  INDETERMINADO, and --strict is non-zero
# ---------------------------------------------------------------------------
def test_string_target_form_is_indeterminado(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_UNMODELLED_FORM},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "INDETERMINADO", sites[0]
    assert sites[0]["form"] == "string-target"


def test_strict_exits_nonzero_on_indeterminado(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_UNMODELLED_FORM},
    )
    lax = _run_cli(root)
    strict = _run_cli(root, "--strict")
    assert lax.returncode == 0, lax.stderr
    assert strict.returncode == 1, (strict.returncode, strict.stdout)


def test_strict_exits_zero_when_nothing_is_indeterminado(tmp_path: Path) -> None:
    """The negative leg: --strict must not fire on a clean tree."""
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_LIVE_LOOKUP},
    )
    assert _run_cli(root, "--strict").returncode == 0


# ---------------------------------------------------------------------------
# The paid incident: the exact shape that aborted the S328 land of pack D.
# ---------------------------------------------------------------------------
def test_s329_incident_shape_precure_is_fragil(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"ledger_provenance.py": CALL_TIME_TARGET},
        {"test_ledger_provenance.py": TEST_PATCHES_TOP_OBJECT.replace(
            "from _lib import subject", "from _lib import ledger_provenance"
        ).replace("subject.emit_rejection", "ledger_provenance.emit_rejection")},
    )
    assert _verdicts(root) == ["FRAGIL"], _sites(root)


def test_s329_incident_shape_postcure_is_lookup_vivo(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"ledger_provenance.py": CALL_TIME_TARGET},
        {"test_ledger_provenance.py": TEST_LIVE_LOOKUP.replace(
            "from _lib import subject", "from _lib import ledger_provenance"
        ).replace("subject.emit_rejection", "ledger_provenance.emit_rejection")},
    )
    assert _verdicts(root) == ["LOOKUP-VIVO"], _sites(root)


# ---------------------------------------------------------------------------
# Additional forms the census must not miss.
# ---------------------------------------------------------------------------
def test_direct_assignment_monkeypatch_is_a_site(tmp_path: Path) -> None:
    """`audit_emit.emit_x = fake` carries the same staleness hazard."""
    body = (
        "from __future__ import annotations\n\n"
        "from _lib import audit_emit\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    audit_emit.emit_generic = lambda **kw: None\n"
        "    subject.emit_rejection('x')\n"
    )
    root = _shadow(
        tmp_path, {"subject.py": CALL_TIME_TARGET}, {"test_subject.py": body}
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["form"] == "direct-assign"
    assert sites[0]["verdict"] == "FRAGIL"
    assert sites[0]["target_expr"] == "audit_emit"
    assert sites[0]["attr"] == "emit_generic"


def test_aliased_import_is_tracked(tmp_path: Path) -> None:
    """`from _lib import audit_emit as ae` must resolve by IMPORT, not name."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import audit_emit as ae\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(ae, 'emit_generic'):\n"
        "        subject.emit_rejection('x')\n"
    )
    root = _shadow(
        tmp_path, {"subject.py": CALL_TIME_TARGET}, {"test_subject.py": body}
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "FRAGIL", sites[0]
    assert sites[0]["target_expr"] == "ae"


def test_consumer_attribute_patch_is_seguro(tmp_path: Path) -> None:
    """Patching the SUBJECT's own attribute is immune to emitter churn."""
    target = (
        '"""Consumer that binds a private alias at import time."""\n\n'
        "from _lib import audit_emit as _audit_emit\n\n\n"
        "def emit_rejection(reason):\n"
        "    _audit_emit.emit_generic(action='rejected')\n"
    )
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(subject, '_audit_emit'):\n"
        "        subject.emit_rejection('x')\n"
    )
    root = _shadow(tmp_path, {"subject.py": target}, {"test_subject.py": body})
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["form"] == "obj-consumer"
    assert sites[0]["verdict"] == "SEGURO"


def test_importlib_resolution_counts_as_call_time(tmp_path: Path) -> None:
    """`importlib.import_module` inside a function is call-time too."""
    target = (
        "import importlib\n\n\n"
        "def emit_rejection(reason):\n"
        "    m = importlib.import_module('_lib.audit_emit')\n"
        "    m.emit_generic(action='rejected')\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": target},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    assert _verdicts(root) == ["FRAGIL"], _sites(root)


# ---------------------------------------------------------------------------
# Instrument hygiene: inputs, JSON shape, exit codes.
# ---------------------------------------------------------------------------
def test_census_prints_its_inputs(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    out = _run_cli(root).stdout
    assert "INPUTS" in out
    assert "test files scanned" in out
    assert "target modules indexed" in out
    assert str(root) in out


def test_json_mode_is_parseable_and_carries_criteria(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    r = _run_cli(root, "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["files_scanned"] == 1
    assert payload["sites"][0]["criterion"]
    assert payload["sites"][0]["inferred_targets"] == ["subject"]


def test_missing_hooks_dir_is_usage_error(tmp_path: Path) -> None:
    r = _run_cli(tmp_path)
    assert r.returncode == 2
    assert "no .claude/hooks" in r.stderr


def test_unparseable_test_file_is_reported_not_swallowed(tmp_path: Path) -> None:
    """A parse failure must SHRINK nothing silently - it exits 3."""
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    _write(root, ".claude/hooks/tests/test_broken.py", "def f(:\n")
    r = _run_cli(root)
    assert r.returncode == 3, (r.returncode, r.stdout)
    assert "test_broken.py" in r.stdout


def test_help_documents_exit_codes() -> None:
    r = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    for code in ("0 =", "1 =", "2 =", "3 ="):
        assert code in r.stdout, r.stdout


# ---------------------------------------------------------------------------
# reload() on a stale alias - the form the first pass MISSED, found by
# reproduction: test_audit_emit_chain_length.py setUp fails with
# "ImportError: module _lib.audit_emit not in sys.modules" under a polluter.
# ---------------------------------------------------------------------------
RELOAD_ON_MODULE_ALIAS = '''\
from __future__ import annotations

import importlib

from _lib import audit_emit              # module-level: STALE-able


def setUp(self):
    importlib.reload(audit_emit)
'''

RELOAD_AFTER_LIVE_REBIND = '''\
from __future__ import annotations

import importlib

from _lib import audit_emit              # module-level, but REBOUND below


def setUp(self):
    global audit_emit
    audit_emit = importlib.reload(importlib.import_module("_lib.audit_emit"))


def test_thing():
    importlib.reload(audit_emit)
'''


def test_reload_on_module_alias_is_fragil(tmp_path: Path) -> None:
    """`reload()` asserts identity against sys.modules - a stale object raises."""
    root = _shadow(
        tmp_path,
        {"subject.py": IMPORT_TIME_TARGET},
        {"test_subject.py": RELOAD_ON_MODULE_ALIAS},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["form"] == "reload-stale"
    assert sites[0]["verdict"] == "FRAGIL", sites[0]
    assert "sys.modules[name] is the SAME object" in sites[0]["criterion"]


def test_reload_verdict_is_independent_of_consumer_kind(tmp_path: Path) -> None:
    """reload fragility does not depend on how the consumer resolves."""
    for target in (CALL_TIME_TARGET, IMPORT_TIME_TARGET):
        root = _shadow(
            tmp_path / str(abs(hash(target))),
            {"subject.py": target},
            {"test_subject.py": RELOAD_ON_MODULE_ALIAS},
        )
        assert _verdicts(root) == ["FRAGIL"], target


def test_setup_live_rebind_downgrades_to_lookup_vivo(tmp_path: Path) -> None:
    """The cure shape already in the tree (spool_drain setUp) is recognised."""
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": RELOAD_AFTER_LIVE_REBIND},
    )
    sites = _sites(root)
    assert sites, "reload site must still be SEEN, just re-judged"
    assert {s["verdict"] for s in sites} == {"LOOKUP-VIVO"}, sites
    reload_sites = [x for x in sites if x["form"] == "reload-stale"]
    assert len(reload_sites) == 1, sites
    crit = reload_sites[0]["criterion"]
    assert "REBOUND from a live import in" in crit, crit
    assert "setUp" in crit and "which owns this site" in crit, crit
    assert any(x["form"] == "live-rebind" for x in sites), sites


def test_live_rebind_outside_setup_does_not_downgrade(tmp_path: Path) -> None:
    """Only a setUp-like rebind runs before EVERY test; a one-off does not."""
    body = RELOAD_AFTER_LIVE_REBIND.replace("def setUp(self):", "def helper():")
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": body},
    )
    assert "FRAGIL" in _verdicts(root), _sites(root)


# ---------------------------------------------------------------------------
# `patch.object(<module under test>._audit_emit, "emit_x")` - the form the
# second pass MISSED. It was being DROPPED silently, which is the failure the
# inverted rule exists to prevent.
# ---------------------------------------------------------------------------
CONSUMER_ALIAS_TARGET = '''\
"""Consumer holding its own import-time alias to the emitter module."""

from _lib import audit_emit as _audit_emit


def emit_rejection(reason):
    _audit_emit.emit_generic(action="rejected")
'''

TEST_PATCHES_CONSUMER_ALIAS = '''\
from __future__ import annotations

import unittest.mock as mock

from _lib import subject


def test_emits():
    with mock.patch.object(subject._audit_emit, "emit_generic") as fake:
        subject.emit_rejection("x")
    assert fake.call_count == 1
'''


def test_patch_on_consumer_alias_object_is_seen_and_seguro(tmp_path: Path) -> None:
    root = _shadow(
        tmp_path,
        {"subject.py": CONSUMER_ALIAS_TARGET},
        {"test_subject.py": TEST_PATCHES_CONSUMER_ALIAS},
    )
    sites = _sites(root)
    assert len(sites) == 1, "the site must not be dropped: %r" % (sites,)
    assert sites[0]["form"] == "obj-consumer"
    assert sites[0]["verdict"] == "SEGURO"


def test_patch_shaped_emitter_mention_is_never_dropped(tmp_path: Path) -> None:
    """Anti-rot: an unmodelled form surfaces as INDETERMINADO, not silence."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    registry = {}\n"
        "    with mock.patch.object(registry['_lib.audit_emit'], 'emit_x'):\n"
        "        pass\n"
    )
    root = _shadow(
        tmp_path, {"subject.py": CALL_TIME_TARGET}, {"test_subject.py": body}
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["form"] == "unmodelled-form"
    assert sites[0]["verdict"] == "INDETERMINADO"


def test_no_patch_shaped_emitter_mention_escapes_the_census(tmp_path: Path) -> None:
    """Independent cross-check on the REAL tree, run as a test.

    Every ``patch``/``patch.object``/``setattr``/``reload`` call whose first
    argument mentions the emitter must appear in the census. A file that stops
    being seen is the failure mode this instrument is least able to notice on
    its own.
    """
    import ast as _ast

    mod = _load_module()
    repo = Path(__file__).resolve().parents[3]
    if not (repo / ".claude" / "hooks" / "tests").is_dir():
        return  # not the framework checkout; nothing to cross-check
    census = mod.run_census(repo)
    seen = {(s["file"], s["line"]) for s in census["sites"]}

    missed = []
    for d in ("hooks/tests", "hooks/_lib/tests"):
        for p in sorted((repo / ".claude" / d).rglob("test_*.py")):
            try:
                tree = _ast.parse(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            rel = str(p.relative_to(repo))
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.Call) or not node.args:
                    continue
                name = mod._dotted(node.func) or ""
                tail = name.split(".")[-1]
                if tail not in ("patch", "object", "setattr", "reload"):
                    continue
                try:
                    a0 = _ast.unparse(node.args[0])
                except Exception:
                    continue
                if "audit_emit" not in a0:
                    continue
                if "import_module" in a0 or "__import__" in a0:
                    # arg0 is itself a LIVE resolution - it cannot be
                    # stale, so it is not a site of this class.
                    continue
                if (rel, node.lineno) not in seen:
                    missed.append("%s:%d  %s" % (rel, node.lineno, a0))
    assert not missed, "sites dropped by the census:\n  " + "\n  ".join(missed)


# ===========================================================================
# Rail round 1, finding 1 - a setUp rebind is scoped to its OWN class, its
# OWN alias, and only when it declares `global`.
# ===========================================================================
TWO_CLASSES_ONE_REBIND = '''\
from __future__ import annotations

import importlib
import unittest

from _lib import audit_emit              # module-level: STALE-able


class ClassA(unittest.TestCase):
    def setUp(self):
        global audit_emit
        audit_emit = importlib.reload(importlib.import_module("_lib.audit_emit"))

    def test_a(self):
        importlib.reload(audit_emit)


class ClassB(unittest.TestCase):
    def setUp(self):
        importlib.reload(audit_emit)

    def test_b(self):
        importlib.reload(audit_emit)
'''


def _by_line(root: Path) -> dict:
    return {s["line"]: s for s in _sites(root)}


def test_setup_rebind_does_not_travel_to_another_class(tmp_path: Path) -> None:
    """The S329 false-safe: ClassB has no rebind of its own."""
    root = _shadow(
        tmp_path,
        {"subject.py": IMPORT_TIME_TARGET},
        {"test_subject.py": TWO_CLASSES_ONE_REBIND},
    )
    lines = TWO_CLASSES_ONE_REBIND.splitlines()
    a_reload = lines.index("        importlib.reload(audit_emit)") + 1
    b_sites = [
        i + 1
        for i, ln in enumerate(lines)
        if ln == "        importlib.reload(audit_emit)" and i + 1 != a_reload
    ]
    assert len(b_sites) == 2, b_sites

    sites = _by_line(root)
    assert sites[a_reload]["verdict"] == "LOOKUP-VIVO", sites[a_reload]
    assert sites[a_reload]["class"] == "ClassA"
    for ln in b_sites:
        assert sites[ln]["verdict"] == "FRAGIL", sites[ln]
        assert sites[ln]["class"] == "ClassB"


def test_setup_rebind_is_scoped_to_the_alias_it_rebinds(tmp_path: Path) -> None:
    """A rebind of `ae` must not vouch for a site on `audit_emit`."""
    body = (
        "from __future__ import annotations\n\n"
        "import importlib\n"
        "import unittest\n\n"
        "from _lib import audit_emit\n"
        "from _lib import audit_emit as ae\n\n\n"
        "class ClassA(unittest.TestCase):\n"
        "    def setUp(self):\n"
        "        global ae\n"
        "        ae = importlib.reload(importlib.import_module('_lib.audit_emit'))\n\n"
        "    def test_a(self):\n"
        "        importlib.reload(audit_emit)\n"
    )
    root = _shadow(
        tmp_path, {"subject.py": IMPORT_TIME_TARGET}, {"test_subject.py": body}
    )
    reloads = [s for s in _sites(root) if s["form"] == "reload-stale"]
    assert len(reloads) == 1, _sites(root)
    assert reloads[0]["verdict"] == "FRAGIL", reloads[0]


def test_rebind_without_global_is_a_local_and_does_not_downgrade(
    tmp_path: Path,
) -> None:
    """No `global` => the assignment binds a LOCAL; the module name stays stale."""
    body = TWO_CLASSES_ONE_REBIND.replace("        global audit_emit\n", "")
    root = _shadow(
        tmp_path, {"subject.py": IMPORT_TIME_TARGET}, {"test_subject.py": body}
    )
    sites = _sites(root)
    forms = {s["form"] for s in sites}
    assert "local-rebind" in forms, sites
    assert "live-rebind" not in forms, sites
    local = [s for s in sites if s["form"] == "local-rebind"][0]
    assert local["verdict"] == "INDETERMINADO", local
    assert "binds a LOCAL" in local["criterion"], local
    # And every reload in the file - ClassA's included - is now FRAGIL.
    assert {s["verdict"] for s in sites if s["form"] == "reload-stale"} == {
        "FRAGIL"
    }, sites


# ===========================================================================
# Rail round 1, finding 2 - consumer ownership must be PROVEN, not assumed
# from an attribute name that merely contains "audit_emit".
# ===========================================================================
DISPATCH_ALIAS_TARGET = '''\
"""Consumer whose `_audit_emit` alias points at a DIFFERENT module."""

from _lib import audit_emit_dispatch as _audit_emit


def emit_rejection(reason):
    _audit_emit.emit_generic(action="rejected")
'''


def test_consumer_base_must_be_resolvable_by_import(tmp_path: Path) -> None:
    """A dynamically loaded module cannot vouch for anything (the `HOOK = _load()` shape)."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "HOOK = object()\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(HOOK._audit_emit, 'emit_generic'):\n"
        "        pass\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": CONSUMER_ALIAS_TARGET},
        {"test_subject.py": body},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["form"] == "obj-consumer"
    assert sites[0]["verdict"] == "INDETERMINADO", sites[0]
    assert "not bound by an import statement" in sites[0]["criterion"], sites[0]


def test_consumer_outside_the_indexed_roots_is_named_as_such(
    tmp_path: Path,
) -> None:
    """An imported consumer the index never scanned is a SCOPE gap, not a
    resolution failure - the criterion must distinguish the two."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib.mcp import canonical_guard\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(canonical_guard._audit_emit, 'emit_generic'):\n"
        "        pass\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": CONSUMER_ALIAS_TARGET},
        {"test_subject.py": body},
    )
    _write(root, ".claude/hooks/_lib/mcp/__init__.py", "")
    _write(root, ".claude/hooks/_lib/mcp/canonical_guard.py", CONSUMER_ALIAS_TARGET)
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "INDETERMINADO", sites[0]
    assert "NOT in the target index" in sites[0]["criterion"], sites[0]
    assert "outside the indexed roots" in sites[0]["criterion"], sites[0]


def test_consumer_alias_object_needs_a_proven_emitter_alias(tmp_path: Path) -> None:
    """`X._audit_emit` patched as an OBJECT while X binds another module."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(subject._audit_emit, 'emit_generic'):\n"
        "        subject.emit_rejection('x')\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": DISPATCH_ALIAS_TARGET,
         "audit_emit_dispatch.py": "def emit_generic(**kw):\n    return None\n"},
        {"test_subject.py": body},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "INDETERMINADO", sites[0]
    assert "not a proven _lib.audit_emit alias" in sites[0]["criterion"], sites[0]


def test_consumer_attribute_name_that_is_not_an_alias_is_seguro(
    tmp_path: Path,
) -> None:
    """`patch.object(X, "_audit_emit")` where X binds audit_emit_dispatch.

    The patch replaces an attribute IN PLACE on X, so no `_lib.audit_emit`
    lookup takes part in it - safe w.r.t. THIS class, and the criterion has
    to say why instead of claiming an alias that does not exist.
    """
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(subject, '_audit_emit'):\n"
        "        subject.emit_rejection('x')\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": DISPATCH_ALIAS_TARGET,
         "audit_emit_dispatch.py": "def emit_generic(**kw):\n    return None\n"},
        {"test_subject.py": body},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "SEGURO", sites[0]
    assert "merely contains" in sites[0]["criterion"], sites[0]


def test_consumer_that_also_resolves_at_call_time_is_indeterminado(
    tmp_path: Path,
) -> None:
    """Mixed consumer: import-time alias AND a call-time re-resolution."""
    mixed = (
        '"""Mixed consumer."""\n\n'
        "from _lib import audit_emit as _audit_emit\n\n\n"
        "def emit_rejection(reason):\n"
        "    _audit_emit.emit_generic(action='rejected')\n\n\n"
        "def emit_other(reason):\n"
        "    from _lib import audit_emit\n"
        "    audit_emit.emit_generic(action='other')\n"
    )
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "from _lib import subject\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(subject, '_audit_emit'):\n"
        "        subject.emit_rejection('x')\n"
    )
    root = _shadow(tmp_path, {"subject.py": mixed}, {"test_subject.py": body})
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "INDETERMINADO", sites[0]
    assert "re-resolves the emitter" in sites[0]["criterion"], sites[0]


def test_aliased_consumer_import_resolves(tmp_path: Path) -> None:
    """`import subject as sj` must still resolve `sj` to the module under test."""
    body = (
        "from __future__ import annotations\n\n"
        "import unittest.mock as mock\n\n"
        "import subject as sj\n\n\n"
        "def test_emits():\n"
        "    with mock.patch.object(sj._audit_emit, 'emit_generic'):\n"
        "        sj.emit_rejection('x')\n"
    )
    root = _shadow(
        tmp_path,
        {"subject.py": CONSUMER_ALIAS_TARGET},
        {"test_subject.py": body},
    )
    sites = _sites(root)
    assert len(sites) == 1, sites
    assert sites[0]["verdict"] == "SEGURO", sites[0]
    assert sites[0]["consumer_module"] == "subject", sites[0]


# ===========================================================================
# Rail round 1, finding 4 - a census root with no test directory is an error.
# ===========================================================================
def test_hooks_without_any_test_dir_is_usage_error(tmp_path: Path) -> None:
    _write(tmp_path, ".claude/hooks/_lib/__init__.py", "")
    _write(tmp_path, ".claude/hooks/_lib/subject.py", CALL_TIME_TARGET)
    r = _run_cli(tmp_path)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "no test root found" in r.stderr, r.stderr


def test_one_present_test_dir_is_enough(tmp_path: Path) -> None:
    """The negative leg: the guard must not fire when a root DOES exist."""
    root = _shadow(
        tmp_path,
        {"subject.py": CALL_TIME_TARGET},
        {"test_subject.py": TEST_PATCHES_TOP_OBJECT},
    )
    r = _run_cli(root)
    assert r.returncode == 0, (r.returncode, r.stderr)
    assert "(ABSENT)" in r.stdout, r.stdout  # _lib/tests is genuinely absent


# ===========================================================================
# Rail round 1, finding 3 - RUNTIME control.
#
# Everything above asks the classifier for its own verdict. This block builds
# a real package, imports it, runs the REAL polluter sequence
# (``sys.modules.pop`` + package-attribute ``delattr`` + fresh import) in THIS
# process, and executes the consumer - then feeds the SAME source bytes to the
# classifier and requires the two to agree. A wrong runtime model shows up as
# a red here even when every AST-label assertion is green.
#
# The shadow package is named ``shadowpkg_<uuid>._lib`` so it can never touch
# the repo's own ``_lib``, while still matching the instrument's importer rule
# (``base.endswith("._lib")``).
# ===========================================================================
import contextlib  # noqa: E402  (kept next to the block that uses it)

RT_EMITTER = '''\
"""Shadow emitter. CALLS records what the REAL emitter received."""

CALLS = []


def emit_generic(**kw):
    CALLS.append(kw)
'''

RT_SUBJECT = '''\
"""A consumer that re-resolves the emitter on EVERY call."""


def emit_rejection(reason):
    from {pkg} import audit_emit          # call-time resolution

    fn = getattr(audit_emit, "emit_generic", None)
    if fn is not None:
        fn(action="rejected", reason=reason)
'''

RT_TEST_STALE = '''\
from __future__ import annotations

import unittest.mock as mock

from {pkg} import audit_emit              # module-level: STALE-able
from {pkg} import subject


def test_emits():
    with mock.patch.object(audit_emit, "emit_generic") as fake:
        subject.emit_rejection("x")
    assert fake.call_count == 1
'''

RT_TEST_LIVE = '''\
from __future__ import annotations

import unittest.mock as mock

from {pkg} import audit_emit              # module-level, but NOT the patch target
from {pkg} import subject


def _live_audit_emit():
    """Resolve the object the consumer will ACTUALLY read, right now."""
    from {pkg} import audit_emit as _ae
    return _ae


def test_emits():
    with mock.patch.object(_live_audit_emit(), "emit_generic") as fake:
        subject.emit_rejection("x")
    assert fake.call_count == 1
'''

RT_TEST_CLASSES = '''\
from __future__ import annotations

import importlib
import unittest

from {pkg} import audit_emit              # module-level: STALE-able


class ClassA(unittest.TestCase):
    def setUp(self):
        global audit_emit
        audit_emit = importlib.reload(importlib.import_module("{pkg}.audit_emit"))

    def test_a(self):
        importlib.reload(audit_emit)


class ClassB(unittest.TestCase):
    def setUp(self):
        importlib.reload(audit_emit)

    def test_b(self):
        pass
'''


def _rt_sources(pkg: str) -> dict:
    """The source bytes used by BOTH legs. One text, two consumers."""
    dotted = pkg + "._lib"
    return {
        "audit_emit.py": RT_EMITTER,
        "subject.py": RT_SUBJECT.format(pkg=dotted),
        "t_stale.py": RT_TEST_STALE.format(pkg=dotted),
        "t_live.py": RT_TEST_LIVE.format(pkg=dotted),
        "t_classes.py": RT_TEST_CLASSES.format(pkg=dotted),
    }


def _rt_tree(tmp_path: Path, pkg: str, sources: dict) -> Path:
    """Write an importable ``<pkg>/_lib/`` package holding `sources`."""
    rt = tmp_path / "rt"
    (rt / pkg / "_lib").mkdir(parents=True, exist_ok=True)
    _write(rt, pkg + "/__init__.py", "")
    _write(rt, pkg + "/_lib/__init__.py", "")
    for name, body in sources.items():
        _write(rt, pkg + "/_lib/" + name, body)
    return rt


@contextlib.contextmanager
def _import_sandbox(rt: Path, pkg: str):
    """Import from `rt`, then remove every trace of `pkg` from the process."""
    sys.path.insert(0, str(rt))
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in [
            n for n in list(sys.modules) if n == pkg or n.startswith(pkg + ".")
        ]:
            sys.modules.pop(name, None)
        try:
            sys.path.remove(str(rt))
        except ValueError:
            pass
        importlib.invalidate_caches()


def _pollute(pkg: str):
    """The measured polluter's exact sequence. Aborts if it would be inert."""
    lib_name = pkg + "._lib"
    mod_name = lib_name + ".audit_emit"
    lib = importlib.import_module(lib_name)
    old = sys.modules[mod_name]
    sys.modules.pop(mod_name)
    delattr(lib, "audit_emit")
    new = importlib.import_module(mod_name)
    assert new is not old, "polluter INERT: the re-import returned the SAME object"
    return old, new


def _classifier_leg(tmp_path: Path, sub: str, sources: dict, test_name: str) -> list:
    """Run the census over the SAME bytes, laid out where it expects them."""
    root = _shadow(
        tmp_path / sub,
        {"audit_emit.py": sources["audit_emit.py"],
         "subject.py": sources["subject.py"]},
        {test_name: sources[test_name.replace("test_", "t_", 1)]},
    )
    return _sites(root)


def test_runtime_hazard_is_real_and_the_classifier_agrees(tmp_path: Path) -> None:
    """RED: a patch on the stale module-level alias never reaches the consumer.

    GREEN: the live-lookup shape does. Both legs EXECUTE; the classifier is
    then required to label them FRAGIL / LOOKUP-VIVO.
    """
    pkg = "shadowpkg_" + uuid.uuid4().hex[:10]
    sources = _rt_sources(pkg)
    rt = _rt_tree(tmp_path, pkg, sources)

    with _import_sandbox(rt, pkg):
        stale = importlib.import_module(pkg + "._lib.t_stale")
        live = importlib.import_module(pkg + "._lib.t_live")
        old, new = _pollute(pkg)

        # The module-level alias of BOTH test modules is now the OLD object.
        assert stale.audit_emit is old
        assert live.audit_emit is old

        # --- RED leg: the patch lands on an object nobody reads -------------
        raised = None
        try:
            stale.test_emits()
        except AssertionError as exc:      # `fake.call_count == 1` fails
            raised = exc
        assert raised is not None, (
            "the stale-alias patch INTERCEPTED the call - the hazard this "
            "instrument is about was not reproduced, so nothing below proves "
            "anything"
        )
        assert len(new.CALLS) == 1, (
            "the REAL emitter should have run on the FRESH module", new.CALLS
        )

        # --- GREEN leg: the live lookup resolves the same object ------------
        del new.CALLS[:]
        live.test_emits()                  # must not raise
        assert new.CALLS == [], (
            "the mock did not intercept: the live-lookup cure does not work",
            new.CALLS,
        )

    stale_src = (rt / pkg / "_lib" / "t_stale.py").read_text(encoding="utf-8")
    live_src = (rt / pkg / "_lib" / "t_live.py").read_text(encoding="utf-8")

    fragil = _classifier_leg(tmp_path, "cls_stale", sources, "test_stale.py")
    vivo = _classifier_leg(tmp_path, "cls_live", sources, "test_live.py")

    # The classifier read the SAME bytes that were just executed.
    assert (
        tmp_path / "cls_stale" / ".claude" / "hooks" / "tests" / "test_stale.py"
    ).read_text(encoding="utf-8") == stale_src
    assert (
        tmp_path / "cls_live" / ".claude" / "hooks" / "tests" / "test_live.py"
    ).read_text(encoding="utf-8") == live_src

    assert [s["verdict"] for s in fragil] == ["FRAGIL"], fragil
    assert [s["verdict"] for s in vivo] == ["LOOKUP-VIVO"], vivo


def test_runtime_setup_rebind_is_order_dependent_and_class_scoped(
    tmp_path: Path,
) -> None:
    """The cross-class case of finding 1, executed.

    ``ClassB.setUp`` reloads the module-level alias it never rebinds. Run
    alone after a polluter it raises ImportError; run after ``ClassA.setUp``
    it succeeds. That is order-dependence, not safety - and the classifier
    must not call ClassB's sites LOOKUP-VIVO.
    """
    pkg = "shadowpkg_" + uuid.uuid4().hex[:10]
    sources = _rt_sources(pkg)
    rt = _rt_tree(tmp_path, pkg, sources)

    with _import_sandbox(rt, pkg):
        mod = importlib.import_module(pkg + "._lib.t_classes")
        _pollute(pkg)

        err = None
        try:
            mod.ClassB("test_b").setUp()
        except ImportError as exc:
            err = exc
        assert err is not None, (
            "ClassB.setUp did NOT raise: the cross-class hazard was not "
            "reproduced"
        )
        assert "not in sys.modules" in str(err), str(err)

        # Same process, same polluter - only the ORDER changes.
        mod.ClassA("test_a").setUp()
        mod.ClassB("test_b").setUp()       # must not raise now

    classes_src = (rt / pkg / "_lib" / "t_classes.py").read_text(encoding="utf-8")
    root = _shadow(
        tmp_path / "cls_classes",
        {"audit_emit.py": sources["audit_emit.py"]},
        {"test_classes.py": classes_src},
    )
    sites = _sites(root)
    by_class = {}
    for s in sites:
        by_class.setdefault(s["class"], []).append(s)

    assert {s["verdict"] for s in by_class["ClassA"]} == {"LOOKUP-VIVO"}, sites
    b_verdicts = {s["verdict"] for s in by_class["ClassB"]}
    assert b_verdicts == {"FRAGIL"}, (
        "ClassB raises ImportError at runtime but the census called it "
        "%r" % (sorted(b_verdicts),)
    )
