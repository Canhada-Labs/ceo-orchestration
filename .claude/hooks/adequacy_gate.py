#!/usr/bin/env python3
"""PLAN-128 Wave-1 #5 — diff-scoped test-adequacy gate (Via Canhada reuse, $0, OPT-IN, advisory).

PLAN-127 killed the aggregate Canhada Score as an AUTHORIZATION signal (omission-blind). It survives here
as an honest QUALITY signal: after the normal verification passes, mutate the CHANGED file and measure how
many mutants the project's OWN tests kill. Low kill-rate → "your tests don't constrain this change → add
tests / cross-review". HONEST BOUNDARY (per PLAN-127 E0): this measures adequacy-FOR-WHAT-THE-TESTS-CHECK,
NOT completeness — it cannot tell you a requirement is MISSING, only that the tests weakly constrain the
code that IS there. Value over coverage: coverage says the line ran; this says a mutation of it would be
caught.

TEMP-COPY-SAFE (Codex 019e8db2 fix #10 — the gate that kept this OUT of the per-edit dispatcher until now):
the previous draft mutated the changed file IN PLACE and restored it in a ``finally``. That is unsafe — a
SIGKILL/OOM/power-loss between the mutate-write and the restore leaves the developer's real file CORRUPTED
with a mutant, and the mutated code runs inside the live workspace. This version NEVER writes the real file.
It copies the changed source (+ its test + bounded same-dir siblings) into an isolated temp sandbox, mutates
the COPY there, runs the tests against the COPY, and removes the sandbox in a ``finally``. The real file is
opened read-only exactly once.

ISOLATION (Codex 019e90ab P1, both fixed):
  • The sandbox pytest runs with PYTHONPATH stripped from its env so a leaked path cannot import the REAL
    module while we mutate only the copy (defence-in-depth; we do NOT set PYTHONNOUSERSITE because pytest
    itself often lives in the user site and disabling it would just fail every run).
  • A CANARY proves the test actually exercises the sandbox copy before we trust any kill-count: we write a
    poison version (raises on import) into the sandbox and run; if the suite still PASSES, the test is NOT
    importing our copy (e.g. it imports a dotted package the flat sandbox can't shadow) → we BAIL SILENT
    rather than report a fabricated weak-test verdict.
  • Every file copied into the sandbox is checked: real (non-symlink) file resolving INSIDE cwd, else skipped
    — a symlinked sibling cannot pull outside-workspace content into the sandbox.

For packages with complex intra-package imports (dotted paths, repo-wide fixtures, editable installs) the
flat sandbox cannot reproduce the import context and the gate is SILENT (baseline-red or canary-survived).
That silence is HONEST, not a pass — treat an un-measurable file as "run the full suite / cross-review", not
as "adequately tested".

OPT-IN (``CEO_ADEQUACY_GATE=1``) — it runs the test suite per mutant (1 baseline + 1 canary + <=MAX_MUTANTS),
so it is materially slower than the per-edit checks (expect tens of seconds on weak tests) and is NOT
default-on. The first time it activates in a process it prints a one-line latency disclosure to stderr.

Self-contained: the mutation operators are vendored from PLAN-126 ``sg_m0_runner.gen_mutants`` (a landed hook
must not import from a ``.claude/plans/`` directory — plans get archived). Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Dict, List, Optional, Tuple

MAX_MUTANTS = 8
MAX_SIBLINGS = 40          # bounded same-dir .py copy; larger dirs → flat src+test only (likely silent)
TEST_TIMEOUT_S = 20
THRESHOLD = 0.5            # kill-rate below this → flag
_CANARY = "\nraise RuntimeError('adequacy_gate_canary')  # sandbox-wiring probe\n"
_DISCLOSED = False        # one-shot stderr latency disclosure per process


# ----------------------------------------------------------------------------------------------
# Vendored mutation engine — operator-for-operator identical to PLAN-126 sg_m0_runner.gen_mutants.
# Source-level, regex-based, AST-validated, de-duped. Stdlib (re + ast) only.
# ----------------------------------------------------------------------------------------------
_LITERAL_OPS: List[Tuple[str, str]] = [
    (" + ", " - "), (" - ", " + "), (" * ", " + "),
    ("==", "!="), ("!=", "=="),
    (" and ", " or "), (" or ", " and "),
    ("True", "False"), ("False", "True"),
    ("min(", "max("), ("max(", "min("),
    ("[1:]", "[2:]"),
]


def _int_sites(src: str):
    return list(re.finditer(r"(?<![\w.])(\d+)(?![\w.])", src))


def _mutate_ints(src: str) -> List[str]:
    out = []
    for m in _int_sites(src):
        v = int(m.group(1))
        for nv in (v + 1, v - 1, 0):
            if nv == v:
                continue
            out.append(src[:m.start()] + str(nv) + src[m.end():])
    return out


def _mutate_literal(src: str, needle: str, repl: str) -> List[str]:
    out = []
    start = 0
    while True:
        i = src.find(needle, start)
        if i < 0:
            break
        out.append(src[:i] + repl + src[i + len(needle):])
        start = i + len(needle)
    return out


def _mutate_lt_gt(src: str) -> List[str]:
    out = []
    for m in re.finditer(r"(?<![<>=!])<(?!=)", src):
        out.append(src[:m.start()] + "<=" + src[m.end():])
    for m in re.finditer(r"(?<![<>=!])>(?!=)", src):
        out.append(src[:m.start()] + ">=" + src[m.end():])
    return out


def _mutate_strings(src: str) -> List[str]:
    out = []
    for m in re.finditer(r"'([^'\\\n]*)'", src):
        out.append(src[:m.start()] + "'" + m.group(1) + "_MUT'" + src[m.end():])
    for m in re.finditer(r'"([^"\\\n]*)"', src):
        out.append(src[:m.start()] + '"' + m.group(1) + '_MUT"' + src[m.end():])
    return out


def _mutate_returns(src: str) -> List[str]:
    out = []
    for m in re.finditer(r"return [^\n]+", src):
        if m.group(0).strip() == "return None":
            continue
        out.append(src[:m.start()] + "return None" + src[m.end():])
    return out


def gen_mutants(reference: str) -> List[str]:
    """All valid, distinct, non-noop source mutants of one file (vendored from PLAN-126 sg_m0)."""
    cands: List[str] = []
    cands += _mutate_ints(reference)
    cands += _mutate_lt_gt(reference)
    cands += _mutate_strings(reference)
    cands += _mutate_returns(reference)
    for needle, repl in _LITERAL_OPS:
        cands += _mutate_literal(reference, needle, repl)
    seen = set()
    out = []
    for c in cands:
        if c == reference or c in seen:
            continue
        try:
            ast.parse(c)
        except SyntaxError:
            continue
        seen.add(c)
        out.append(c)
    return out


# ----------------------------------------------------------------------------------------------
# Hook.
# ----------------------------------------------------------------------------------------------
def _allow(extra: Optional[str] = None) -> Dict:
    if extra:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": extra}}
    return {}


def find_test_file(src: str, cwd: str) -> Optional[str]:
    base = os.path.basename(src)
    stem = base[:-3] if base.endswith(".py") else base
    d = os.path.dirname(src)
    cands = [os.path.join(d, "test_%s.py" % stem), os.path.join(d, "%s_test.py" % stem),
             os.path.join(d, "tests", "test_%s.py" % stem),
             os.path.join(cwd, "tests", "test_%s.py" % stem)]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def _safe_to_copy(path: str, cwd: str) -> bool:
    """Copy a candidate into the sandbox ONLY if it is a real (non-symlink) file resolving inside cwd —
    a symlinked sibling/test/conftest must not pull outside-workspace content in (Codex 019e90ab P1)."""
    try:
        if os.path.islink(path):
            return False
        rp = os.path.realpath(path)
        return os.path.isfile(rp) and (rp == cwd or rp.startswith(cwd + os.sep))
    except OSError:
        return False


def default_test_runner(testfile: str, cwd: str) -> int:
    """Run the project's tests for `testfile` with PYTHONPATH stripped so a leaked path cannot import the
    real module while we mutate only the sandbox copy (Codex 019e90ab P1, defence-in-depth; the CANARY in
    adequacy() is the robust guarantee). We do NOT set PYTHONNOUSERSITE — pytest itself often lives in the
    user site, and disabling it would just make every run fail-to-discover. rc 0 = pass (mutant survived),
    >0 = fail (mutant killed), <0 = could-not-run (timeout/infra) → never counted as a kill."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", os.path.basename(testfile)],
                           cwd=cwd, capture_output=True, text=True, timeout=TEST_TIMEOUT_S, env=env)
        return p.returncode
    except (subprocess.TimeoutExpired, OSError):
        return -1


def _populate_sandbox(sandbox: str, src: str, original: str, testfile: str, cwd: str) -> str:
    """Copy the source-under-test (+ bounded non-symlink same-dir siblings + the test + same-dir conftest)
    into the isolated sandbox. Returns the run-target path. NEVER touches the real workspace."""
    base = os.path.basename(src)
    srcdir = os.path.dirname(src) or "."
    try:
        sibs = [f for f in os.listdir(srcdir) if f.endswith(".py")]
    except OSError:
        sibs = []
    if len(sibs) <= MAX_SIBLINGS:
        for f in sibs:
            sp = os.path.join(srcdir, f)
            if _safe_to_copy(sp, cwd):
                try:
                    shutil.copyfile(sp, os.path.join(sandbox, f))
                except OSError:
                    pass
    # the changed source ALWAYS wins (written last from the in-memory original we already read).
    with open(os.path.join(sandbox, base), "w", encoding="utf-8") as fh:
        fh.write(original)
    run_target = testfile
    if os.path.isfile(testfile) and _safe_to_copy(testfile, cwd):
        tbase = os.path.basename(testfile)
        shutil.copyfile(testfile, os.path.join(sandbox, tbase))
        run_target = os.path.join(sandbox, tbase)
        for cdir in (os.path.dirname(testfile), srcdir):
            cpath = os.path.join(cdir, "conftest.py")
            if _safe_to_copy(cpath, cwd):
                try:
                    shutil.copyfile(cpath, os.path.join(sandbox, "conftest.py"))
                except OSError:
                    pass
    return run_target


def adequacy(src: str, cwd: str, runner: Optional[Callable[[str, str], int]] = None,
             testfile: Optional[str] = None) -> Dict:
    runner = runner or default_test_runner
    # Normalise both to realpath so the containment check is symlink-stable regardless of caller
    # (e.g. macOS /tmp → /private/tmp); gate() already realpaths, but adequacy() must be self-safe.
    src = os.path.realpath(src)
    cwd = os.path.realpath(cwd)
    if not src.endswith(".py") or not os.path.isfile(src):
        return _allow()
    testfile = testfile or find_test_file(src, cwd)
    if testfile is None:
        return _allow("ADEQUACY: the changed file %s has no discoverable test — add tests or cross-review "
                      "before trusting it." % os.path.basename(src))
    original = open(src, "r", encoding="utf-8").read()
    mutants = gen_mutants(original)[:MAX_MUTANTS]
    if not mutants:
        return _allow()
    base = os.path.basename(src)
    sandbox = os.path.realpath(tempfile.mkdtemp(prefix="ceo-adequacy-"))
    killed = measured = 0
    try:
        run_target = _populate_sandbox(sandbox, src, original, testfile, cwd)
        sbox_src = os.path.join(sandbox, base)
        # baseline must pass in the ISOLATED sandbox, else we cannot measure adequacy honestly → silent.
        if runner(run_target, sandbox) != 0:
            return _allow()
        # CANARY: prove the test actually exercises OUR copy. Poison it; if the suite still passes, the test
        # is importing something else (dotted package / editable install the flat sandbox can't shadow) →
        # any kill-count would be fabricated → BAIL SILENT (Codex 019e90ab P1).
        with open(sbox_src, "w", encoding="utf-8") as fh:
            fh.write(original + _CANARY)
        if runner(run_target, sandbox) == 0:
            return _allow()
        for mut in mutants:
            with open(sbox_src, "w", encoding="utf-8") as fh:    # the COPY, never the real file
                fh.write(mut)
            rc = runner(run_target, sandbox)
            if rc == 0:
                measured += 1                # tests passed → mutant SURVIVED (a real adequacy gap)
            elif rc > 0:
                measured += 1; killed += 1   # tests failed → mutant KILLED
            # rc < 0 = timeout/infra → SKIP, never counted as a kill (no fabricated adequacy)
    finally:
        try:
            shutil.rmtree(sandbox)
        except OSError as exc:
            sys.stderr.write("# adequacy_gate sandbox cleanup failed: %s\n" % str(exc)[:120])
    if measured == 0:
        return _allow()                      # couldn't measure (all timed out / sandbox unusable) → silent
    rate = killed / measured
    if rate < THRESHOLD:
        try:  # PLAN-128 §7 — fail-open catch telemetry (never blocks the hook)
            _alib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lib")
            if _alib not in sys.path:
                sys.path.insert(0, _alib)
            import audit_emit as _ae
            _ae.emit_generic("adequacy_gate_flag", flag_reason="weak_assertion",
                             lang="python", flag_count=int(measured - killed))
        except Exception:
            pass
        return _allow("ADEQUACY (Via Canhada): your tests for %s killed only %d/%d measurable mutations "
                      "(%.0f%%) — they weakly constrain this change. Add tests for the un-caught behavior, "
                      "or get a cross-model review, before trusting it. (Measures test strength on what's "
                      "there, NOT missing requirements.)" % (base, killed, measured, rate * 100))
    return _allow()


def _disclose_once() -> None:
    global _DISCLOSED
    if not _DISCLOSED:
        _DISCLOSED = True
        sys.stderr.write(
            "# ADEQUACY GATE ON (CEO_ADEQUACY_GATE=1): after a clean verify it runs your test suite "
            "1 baseline + 1 canary + up to %d mutants per edited .py — expect tens of seconds on weak "
            "tests. Disable with CEO_ADEQUACY_GATE=0.\n" % MAX_MUTANTS)


def gate(hook_input: Dict) -> Dict:
    if os.environ.get("CEO_ADEQUACY_GATE") != "1":     # OPT-IN
        return _allow()
    _disclose_once()
    ti = hook_input.get("tool_input") or {}
    cwd = os.path.realpath(hook_input.get("cwd") or os.getcwd())
    fp = ti.get("file_path") or ti.get("path")
    if not isinstance(fp, str):
        return _allow()
    rp = os.path.realpath(fp if os.path.isabs(fp) else os.path.join(cwd, fp))
    # realpath, regular file, UNDER cwd — never read/measure a file outside the workspace.
    if not os.path.isfile(rp) or not (rp == cwd or rp.startswith(cwd + os.sep)):
        return _allow()
    return adequacy(rp, cwd)


def main() -> None:
    try:
        hi = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}"); return
    try:
        print(json.dumps(gate(hi)))
    except Exception as exc:
        sys.stderr.write("# adequacy_gate fail-open: %s\n" % str(exc)[:120])
        print("{}")


# ------------------------------------------------------------------------------------------------
def _selftest() -> None:
    SRC = "def price(x):\n    return x * 9 // 10\n"
    d = os.path.realpath(tempfile.mkdtemp())
    src = os.path.join(d, "calc.py")
    open(src, "w").write(SRC)

    # The runner reads the file-under-test from the SANDBOX (cwd/calc.py), proving we mutate the COPY only;
    # the canary poison line makes exec() raise → returns 1 (killed) → wiring confirmed.
    def strong_runner(testfile, cwd):
        ns = {}
        try:
            exec(open(os.path.join(cwd, "calc.py")).read(), ns)
            ok = ns["price"](100) == 90 and ns["price"](50) == 45 and ns["price"](200) == 180
            return 0 if ok else 1
        except Exception:
            return 1

    r = adequacy(src, d, runner=strong_runner, testfile="dummy")
    # temp-copy-safety: the REAL file is byte-identical (never written), not merely "restored".
    assert open(src).read() == SRC, "real file must be untouched (temp-copy-safe)"
    assert "weakly constrain" not in json.dumps(r), ("strong tests should not flag", r)

    def weak_runner(testfile, cwd):
        ns = {}
        try:
            exec(open(os.path.join(cwd, "calc.py")).read(), ns)
            return 0 if isinstance(ns["price"](100), int) else 1
        except Exception:
            return 1

    r2 = adequacy(src, d, runner=weak_runner, testfile="dummy")
    assert "weakly constrain" in json.dumps(r2), ("weak tests should flag", r2)
    assert open(src).read() == SRC, "real file untouched after weak run too"

    # CANARY: a runner that NEVER imports our copy (ignores it) must NOT be trusted → silent, never a flag.
    def blind_runner(testfile, cwd):
        return 0   # always "passes" regardless of the file under test → canary survives → bail
    r_blind = adequacy(src, d, runner=blind_runner, testfile="dummy")
    assert r_blind == {}, ("canary must bail when the test ignores our copy", r_blind)

    # baseline-fails (sandbox can't run green) → SILENT, never a fabricated verdict.
    r_bad = adequacy(src, d, runner=lambda t, c: 1, testfile="dummy")
    assert r_bad == {}, ("baseline-red must be silent", r_bad)

    # no test file → advisory to add tests.
    r3 = adequacy(src, d, runner=lambda t, c: 0 if "canary" not in open(os.path.join(c, "calc.py")).read()
                  else 1, testfile=None)
    assert "no discoverable test" in json.dumps(r3), r3

    # symlink sibling must NOT be copied (containment).
    outside = os.path.join(os.path.realpath(tempfile.mkdtemp()), "secret.py")
    open(outside, "w").write("SECRET = 1\n")
    link = os.path.join(d, "linked.py")
    try:
        os.symlink(outside, link)
        assert _safe_to_copy(link, d) is False, "symlink outside cwd must be rejected"
    except (OSError, NotImplementedError):
        pass

    # opt-in: gate is silent unless CEO_ADEQUACY_GATE=1.
    prev = os.environ.pop("CEO_ADEQUACY_GATE", None)
    try:
        assert gate({"tool_input": {"file_path": src}, "cwd": d}) == {}
    finally:
        if prev is not None:
            os.environ["CEO_ADEQUACY_GATE"] = prev

    # the vendored engine actually produces (and AST-validates) mutants.
    muts = gen_mutants(SRC)
    assert muts and all(isinstance(m, str) for m in muts), "vendored gen_mutants must yield valid mutants"
    assert SRC not in muts, "no-op mutant must be filtered"

    shutil.rmtree(d, ignore_errors=True)
    print("adequacy_gate.py selftest PASS "
          "(temp-copy-safe / strong-silent / weak-flag / canary-bail / baseline-red-silent / "
          "no-test-advisory / symlink-rejected / opt-in / vendored-engine)")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
