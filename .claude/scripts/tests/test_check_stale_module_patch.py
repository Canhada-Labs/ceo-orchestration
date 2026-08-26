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

import importlib.util
import json
import subprocess
import sys
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
    assert "REBOUND from a live import in setUp" in reload_sites[0]["criterion"]
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
