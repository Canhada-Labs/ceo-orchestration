"""ADR-163 Amendment (PLAN-169 S328) — the runner-normalized SECOND KEY.

The absolute p95 ceiling cannot tell "the hooks got slower" from "the runner
got slower", and the ADR-163 contention pre-probe that was supposed to
separate them measures ``python3 -c pass`` — process CREATION. Field
evidence: ``check_output_secrets`` p95 361.4 / 424.8 / 229.1 ms against the
180 ms ceiling while that probe read UNCONTENDED at 7.76 ms, on hook bytes
that measured 70-77 ms locally and PASSED 3.5 h earlier.

These tests exercise the cure at the PREDICATE level. Nothing here measures
wall-clock: ``run_hook_latency`` takes an injected ``sampler(entry, kind,
index) -> ms`` that replaces every subprocess, so a "+150 ms regression" is
an exact input, not a race with the machine. The two tests that DO need the
real measurement path (the env-scrub control) mock ``subprocess.run`` and
inspect what it was handed.

Phase 1 is what ships: labels are published, exit codes are byte-identical
to today. Every phase-1 test therefore asserts the exit against a
NO-FLAGS run of the same sampler rather than against a recalled constant.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude" / "scripts" / "profile-opus-4-7.py"

# ``_lib.testing`` (TestEnvContext) must be importable: a bare
# unittest.TestCase is an env-hygiene violation in this tree.
_HOOKS_DIR = str(_REPO / ".claude" / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("profile_opus_4_7_rel", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()

_CORPUS_NAMES = (
    "check_agent_spawn",
    "check_anti_ceo_overhead[observe=unset]",
    "check_anti_ceo_overhead[observe=1]",
    "check_output_secrets[observe=unset]",
    "check_output_secrets[observe=1]",
)
_HEAVY = "check_output_secrets[observe=1]"

# Baseline shape used by every scenario: a hook at 70 ms against a reference
# at 50 ms is the locally MEASURED shape (hook p50 70-77 ms; the frozen
# reference measured p50 52.5 ms on this machine), so R_baseline ~= 1.4.
_HOOK_BASELINE_MS = 70.0
_REF_BASELINE_MS = 50.0
# K used by the phase-2 scenarios. NOT a derived value — no paired series
# exists yet; it is 1.25 x R_baseline, the shape the derivation procedure
# will use once an advisory window supplies real pairs.
_K_UNDER_TEST = 1.75
_ITERATIONS = 22  # smallest N past the ADR-163 percentile precondition


class _Sampler:
    """Injected measurement source. Records every call in ORDER.

    ``hook`` / ``ref`` accept a scalar, a ``{entry: value}`` map (with ``"*"``
    as the default), or a ``callable(entry, index)``.
    """

    def __init__(self, hook: Any = _HOOK_BASELINE_MS, ref: Any = _REF_BASELINE_MS):
        self.hook = hook
        self.ref = ref
        self.calls: List[Tuple[str, str, int]] = []

    def __call__(self, entry: str, kind: str, index: int) -> float:
        self.calls.append((entry, kind, index))
        return self._resolve(self.ref if kind == "ref" else self.hook, entry, index)

    @staticmethod
    def _resolve(spec: Any, entry: str, index: int) -> float:
        if callable(spec):
            return float(spec(entry, index))
        if isinstance(spec, dict):
            spec = spec.get(entry, spec.get("*", 0.0))
        if callable(spec):
            return float(spec(entry, index))
        return float(spec)


def _fake_repo(td: str) -> Path:
    """Corpus hooks as stubs, and NO tool_lifecycle.py.

    ``observe_rail_present`` is therefore False and both observe controls are
    structurally green — the verdict under test is the latency predicate
    alone, never a control failure leaking in.
    """
    hooks = Path(td) / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in (
        "check_agent_spawn.py",
        "check_anti_ceo_overhead.py",
        "check_output_secrets.py",
    ):
        (hooks / name).write_text("# stub corpus hook (test)\n")
    return Path(td)


def _run(sampler: Optional[_Sampler] = None, **kwargs: Any) -> Dict[str, Any]:
    """run_hook_latency against a throwaway fake repo."""
    kwargs.setdefault("iterations", _ITERATIONS)
    with tempfile.TemporaryDirectory() as td:
        return MOD.run_hook_latency(_fake_repo(td), sampler=sampler, **kwargs)


def _run_cli(argv_tail: List[str], sampler: _Sampler) -> Tuple[int, Dict[str, Any]]:
    """Drive ``main()`` end-to-end so the EXIT CODE mapping is under test.

    ``run_hook_latency`` is wrapped (not replaced) so the real classifier,
    the real aggregation and the real exit mapping all run; only the
    measurement source is injected.
    """
    real = MOD.run_hook_latency
    captured: Dict[str, Any] = {}

    def _wrapped(*a: Any, **kw: Any) -> Dict[str, Any]:
        kw["sampler"] = sampler
        report = real(*a, **kw)
        captured.update(report)
        return report

    with tempfile.TemporaryDirectory() as td:
        root = _fake_repo(td)
        argv = [
            "profile-opus-4-7.py",
            "--hook-latency",
            "--latency-iterations",
            str(_ITERATIONS),
            "--repo-root",
            str(root),
        ] + argv_tail
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(MOD, "run_hook_latency", _wrapped), mock.patch.object(
            sys, "argv", argv
        ), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = MOD.main()
    captured["_stderr"] = err.getvalue()
    captured["_stdout"] = out.getvalue()
    return rc, captured


def _k_file(td: str, entries: Dict[str, Dict[str, Any]]) -> str:
    path = Path(td) / "k.json"
    path.write_text(
        json.dumps({"entries": entries, "derived_from": {"note": "unit test"}}),
        encoding="utf-8",
    )
    return str(path)


# ---------------------------------------------------------------------------
# Closed sets + the frozen reference's anti-coupling contract
# ---------------------------------------------------------------------------


def _ref_forbidden_imports(source: str) -> List[str]:
    """AST-walk a reference source; return every framework import found.

    This is the checker the anti-coupling test exercises in BOTH directions:
    green on the shipped source, RED on a planted framework import.
    """
    found: List[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_framework_module(alias.name):
                    found.append("import %s" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and node.level > 0:
                found.append("relative import (level %d)" % node.level)
            elif _is_framework_module(module):
                found.append("from %s import ..." % module)
    return found


def _is_framework_module(name: str) -> bool:
    parts = name.split(".")
    return any(p == "_lib" or p == "hooks" or p.startswith("_lib") for p in parts)


class TestClosedSetsAndReferenceShape(TestEnvContext):
    def test_outcome_label_set_is_exactly_four(self):
        self.assertEqual(len(MOD._OUTCOME_LABELS), 4)
        self.assertEqual(len(set(MOD._OUTCOME_LABELS)), 4)
        self.assertEqual(
            set(MOD._OUTCOME_LABELS),
            {
                "pass",
                "advisory_slow_runner",
                "real_regression",
                "infrastructure_contended",
            },
        )

    def test_exit_map_and_precedence_derive_from_the_label_set(self):
        self.assertEqual(set(MOD._LABEL_EXIT_CLASS), set(MOD._OUTCOME_LABELS))
        self.assertEqual(set(MOD._LABEL_PRECEDENCE), set(MOD._OUTCOME_LABELS))
        self.assertEqual(
            [MOD._LABEL_EXIT_CLASS[label] for label in MOD._OUTCOME_LABELS],
            [0, 0, 1, 5],
        )
        # A proven regression outranks contention outranks amnesty.
        self.assertEqual(MOD._LABEL_PRECEDENCE[0], "real_regression")
        self.assertEqual(
            MOD._aggregate_label(["pass", "advisory_slow_runner", "real_regression"]),
            "real_regression",
        )
        self.assertEqual(
            MOD._aggregate_label(["pass", "infrastructure_contended"]),
            "infrastructure_contended",
        )

    def test_reference_never_imports_the_framework(self):
        source = MOD._REF_EXEC_SOURCE
        self.assertEqual(
            _ref_forbidden_imports(source),
            [],
            "the frozen reference must import NOTHING from the hook tree: "
            "the class this gate catches IS an eager framework import, which "
            "would inflate numerator AND denominator",
        )
        # Belt and braces: the literal strings are absent too.
        self.assertNotIn("_lib", source)
        self.assertNotIn(".claude/hooks", source)
        # ...and it really is a parseable, runnable program.
        compile(source, "<ref>", "exec")

    def test_anti_coupling_checker_is_not_vacuous(self):
        """Positive control: the checker must go RED on a planted import."""
        planted = MOD._REF_EXEC_SOURCE.replace(
            "import os\nimport sys\n",
            "import os\nimport sys\nfrom _lib import audit_emit\n",
            1,
        )
        self.assertNotEqual(planted, MOD._REF_EXEC_SOURCE, "plant did not apply")
        findings = _ref_forbidden_imports(planted)
        self.assertTrue(findings, "planted `from _lib import ...` must be caught")
        self.assertIn("_lib", findings[0])

    def test_reference_has_all_three_terms(self):
        source = MOD._REF_EXEC_SOURCE
        for term in ("def term_imports(", "def term_cpu(", "def term_io("):
            self.assertIn(term, source)
        for primitive in ("re.compile", "hashlib.sha256", "os.fsync", "os.replace"):
            self.assertIn(primitive, source)

    def test_reference_sample_floor(self):
        self.assertGreaterEqual(MOD._REF_SAMPLES_PER_ENTRY, 40)

    def test_reference_terms_stay_above_the_calibrated_floor(self):
        """Static anti-rot guard on the term sizing — no wall-clock here.

        Measured on 2026-08-25 (macOS, N=30): the first draft (4000 rounds /
        6 IO cycles) put the reference at p50 34ms of which only 30% was
        EXECUTION — barely more than the ``python3 -c pass`` spawn probe it
        exists to replace, which would leave the ratio nearly as blind. The
        shipped sizing is ~46ms / ~48% execution. Shrinking these constants
        back re-creates that blindness silently, so it must turn a test RED.
        """
        rounds = int(re.search(r"_HASH_ROUNDS = (\d+)", MOD._REF_EXEC_SOURCE).group(1))
        cycles = int(re.search(r"_IO_CYCLES = (\d+)", MOD._REF_EXEC_SOURCE).group(1))
        self.assertGreaterEqual(rounds, 14000, "CPU term shrank below calibration")
        self.assertGreaterEqual(cycles, 24, "IO term shrank below calibration")

    def test_ref_schedule_totals_exactly_and_spreads(self):
        for iterations in (22, 30, 200):
            plan = MOD._ref_schedule(iterations, MOD._REF_SAMPLES_PER_ENTRY)
            self.assertEqual(len(plan), iterations)
            self.assertEqual(
                sum(plan),
                MOD._REF_SAMPLES_PER_ENTRY,
                "schedule must land on exactly n_ref at iterations=%d" % iterations,
            )
            self.assertTrue(all(v >= 0 for v in plan))


# ---------------------------------------------------------------------------
# (f) ref_source_sha256 — stability + positive control
# ---------------------------------------------------------------------------


class TestReferenceSourceHash(TestEnvContext):
    def test_hash_is_stable_across_calls_and_matches_the_report(self):
        first = MOD.ref_source_sha256()
        second = MOD.ref_source_sha256()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        report = _run(_Sampler(), exec_reference=True, relative_advisory=True)
        self.assertEqual(report["ref_source_sha256"], first)

    def test_hash_changes_when_the_reference_text_changes(self):
        """Positive control: mutate ONE constant in a COPY of the source.

        The anchor is a REGEX on ``_HASH_ROUNDS = <n>``, not the literal
        value: retuning the term must not silently disarm this control.
        """
        match = re.search(r"_HASH_ROUNDS = (\d+)", MOD._REF_EXEC_SOURCE)
        self.assertIsNotNone(match, "the reference must carry _HASH_ROUNDS")
        bumped = "_HASH_ROUNDS = %d" % (int(match.group(1)) + 1)
        mutated = (
            MOD._REF_EXEC_SOURCE[: match.start()]
            + bumped
            + MOD._REF_EXEC_SOURCE[match.end():]
        )
        self.assertNotEqual(
            mutated, MOD._REF_EXEC_SOURCE, "the mutated constant must exist"
        )
        mutated_sha = hashlib.sha256(mutated.encode("utf-8")).hexdigest()
        self.assertNotEqual(
            mutated_sha,
            MOD.ref_source_sha256(),
            "a heavier reference silently LOOSENS the relative key; the "
            "report hash is what makes that edit visible",
        )


# ---------------------------------------------------------------------------
# Round-robin interleaving
# ---------------------------------------------------------------------------


class TestRoundRobinInterleaving(TestEnvContext):
    def test_reference_samples_are_spread_through_the_hook_loop(self):
        sampler = _Sampler()
        _run(sampler, exec_reference=True, relative_advisory=True)

        per_entry: Dict[str, List[str]] = {}
        for entry, kind, _index in sampler.calls:
            per_entry.setdefault(entry, []).append(kind)

        self.assertEqual(set(per_entry), set(_CORPUS_NAMES))
        for entry, kinds in per_entry.items():
            self.assertEqual(
                kinds.count("ref"),
                MOD._REF_SAMPLES_PER_ENTRY,
                "%s: every entry gets its own reference series" % entry,
            )
            positions = [i for i, k in enumerate(kinds) if k == "ref"]
            gaps = [b - a for a, b in zip(positions, positions[1:])]
            # k = warm samples per reference sample; a run that hoisted the
            # reference into one pre-loop block (the S318 probe bug) would
            # show one huge gap here.
            k = max(1, _ITERATIONS // MOD._REF_SAMPLES_PER_ENTRY)
            self.assertLessEqual(max(gaps), 2 * k + 1, "%s: reference not interleaved" % entry)
            self.assertLess(
                positions[0], len(kinds) // 4, "%s: reference starts late" % entry
            )
            self.assertGreater(
                positions[-1],
                3 * len(kinds) // 4,
                "%s: reference stops early" % entry,
            )


# ---------------------------------------------------------------------------
# (a) the +150 ms plant
# ---------------------------------------------------------------------------


class TestPlantedRegression(TestEnvContext):
    """(a) heavy entry at baseline+150 ms, reference FLAT => real_regression."""

    def _sampler(self) -> _Sampler:
        return _Sampler(
            hook={_HEAVY: _HOOK_BASELINE_MS + 150.0, "*": _HOOK_BASELINE_MS},
            ref=_REF_BASELINE_MS,
        )

    def test_phase2_labels_real_regression_and_exits_1(self):
        with tempfile.TemporaryDirectory() as td:
            k_path = _k_file(td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES})
            rc, report = _run_cli(
                ["--exec-reference", "--relative-advisory", "--relative-k-source", k_path],
                self._sampler(),
            )
        self.assertEqual(report["phase"], "2-enforcing")
        self.assertEqual(report["hooks"][_HEAVY]["verdict_label"], "real_regression")
        self.assertIs(report["hooks"][_HEAVY]["rel_ok"], False)
        # The unplanted entries stay clean — the verdict is per-entry.
        for name in _CORPUS_NAMES:
            if name != _HEAVY:
                self.assertEqual(report["hooks"][name]["verdict_label"], "pass")
        self.assertEqual(report["verdict_label"], "real_regression")
        self.assertEqual(rc, 1)

    def test_phase1_labels_real_regression_and_keeps_todays_exit(self):
        rc_today, _ = _run_cli([], self._sampler())
        rc_phase1, report = _run_cli(
            ["--exec-reference", "--relative-advisory"], self._sampler()
        )
        self.assertEqual(report["phase"], "1-advisory")
        self.assertEqual(report["hooks"][_HEAVY]["verdict_label"], "real_regression")
        self.assertIsNone(report["hooks"][_HEAVY]["rel_ok"])
        self.assertEqual(
            rc_phase1, rc_today, "phase 1 must not move the exit code"
        )
        self.assertEqual(rc_today, 1, "a 220ms p95 breaches the 180ms ceiling today")


# ---------------------------------------------------------------------------
# (b) the slow runner
# ---------------------------------------------------------------------------


class TestSlowRunnerAmnesty(TestEnvContext):
    """(b) hook AND reference both x3 => advisory_slow_runner under K."""

    def _sampler(self) -> _Sampler:
        return _Sampler(hook=_HOOK_BASELINE_MS * 3, ref=_REF_BASELINE_MS * 3)

    def test_phase2_grants_amnesty_and_exits_0(self):
        with tempfile.TemporaryDirectory() as td:
            k_path = _k_file(td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES})
            rc, report = _run_cli(
                ["--exec-reference", "--relative-advisory", "--relative-k-source", k_path],
                self._sampler(),
            )
        for name in _CORPUS_NAMES:
            stats = report["hooks"][name]
            self.assertEqual(stats["verdict_label"], "advisory_slow_runner", name)
            self.assertIs(stats["rel_ok"], True, name)
            self.assertGreater(stats["p95_ms"], report["p95_ceiling_ms"])
        self.assertEqual(report["verdict_label"], "advisory_slow_runner")
        self.assertEqual(rc, 0)
        self.assertIn("::warning::hook latency AMNESTY", report["_stderr"])
        self.assertIn("SUMMARY:", report["_stderr"])

    def test_phase1_still_reads_real_regression_and_keeps_todays_exit(self):
        """DOCUMENTED phase-1 behaviour: no K, so the absolute key rules."""
        rc_today, _ = _run_cli([], self._sampler())
        rc_phase1, report = _run_cli(
            ["--exec-reference", "--relative-advisory"], self._sampler()
        )
        self.assertEqual(report["hooks"][_HEAVY]["verdict_label"], "real_regression")
        self.assertEqual(rc_phase1, rc_today)
        self.assertEqual(rc_today, 1)

    def test_backstop_denies_amnesty_above_600ms(self):
        """A runner slow enough to be unusable fails even with rel_ok."""
        sampler = _Sampler(hook=650.0, ref=500.0)
        with tempfile.TemporaryDirectory() as td:
            k_path = _k_file(td, {n: {"K": 2.0} for n in _CORPUS_NAMES})
            rc, report = _run_cli(
                ["--exec-reference", "--relative-advisory", "--relative-k-source", k_path],
                sampler,
            )
        self.assertEqual(report["hooks"][_HEAVY]["verdict_label"], "real_regression")
        self.assertIs(report["hooks"][_HEAVY]["rel_ok"], True)
        self.assertEqual(report["abs_backstop_ms"], 600.0)
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# (c) broken reference
# ---------------------------------------------------------------------------


class TestBrokenReference(TestEnvContext):
    """(c) an untrustworthy reference is CONTENDED, never a pass."""

    @staticmethod
    def _k_entries() -> Dict[str, Dict[str, Any]]:
        return {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}

    def test_ref_p50_zero_reads_contended_without_dividing_by_zero(self):
        sampler = _Sampler(hook=_HOOK_BASELINE_MS, ref=0.0)
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, self._k_entries()),
                ],
                sampler,
            )
        for name in _CORPUS_NAMES:
            stats = report["hooks"][name]
            self.assertEqual(stats["verdict_label"], "infrastructure_contended", name)
            self.assertIs(stats["ref_valid"], False, name)
            self.assertIsNone(stats["R_e"], name)
        self.assertEqual(rc, 5)

    def test_split_half_drift_above_threshold_reads_contended(self):
        half = MOD._REF_SAMPLES_PER_ENTRY // 2

        def _drifting(_entry: str, index: int) -> float:
            return 50.0 if index < half else 80.0  # ratio 1.6 > 1.5

        sampler = _Sampler(hook=_HOOK_BASELINE_MS, ref=_drifting)
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, self._k_entries()),
                ],
                sampler,
            )
        stats = report["hooks"][_HEAVY]
        self.assertEqual(stats["verdict_label"], "infrastructure_contended")
        self.assertAlmostEqual(stats["ref_split_half_drift"], 1.6, places=3)
        self.assertEqual(rc, 5)

    def test_drift_just_below_threshold_still_gates(self):
        """Boundary control: 1.5 is INSIDE (<=), so the key still applies."""
        half = MOD._REF_SAMPLES_PER_ENTRY // 2

        def _drifting(_entry: str, index: int) -> float:
            return 50.0 if index < half else 75.0  # ratio exactly 1.5

        sampler = _Sampler(hook=_HOOK_BASELINE_MS, ref=_drifting)
        report = _run(sampler, exec_reference=True, relative_advisory=True)
        stats = report["hooks"][_HEAVY]
        self.assertAlmostEqual(stats["ref_split_half_drift"], 1.5, places=3)
        self.assertEqual(stats["verdict_label"], "pass")
        self.assertIs(stats["ref_valid"], True)

    def test_auto_cap_reads_contended_and_never_passes(self):
        sampler = _Sampler()
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--wall-budget-seconds",
                    "0",
                    "--relative-k-source",
                    _k_file(td, self._k_entries()),
                ],
                sampler,
            )
        self.assertTrue(report["wall_exceeded"])
        self.assertEqual(report["verdict_label"], "infrastructure_contended")
        self.assertFalse(report["passed"])
        self.assertEqual(rc, 5)
        self.assertEqual(
            sampler.calls, [], "the cap must fire BEFORE any measurement"
        )

    def test_auto_cap_in_phase1_keeps_a_nonzero_exit(self):
        rc, report = _run_cli(
            [
                "--exec-reference",
                "--relative-advisory",
                "--wall-budget-seconds",
                "0",
            ],
            _Sampler(),
        )
        self.assertTrue(report["wall_exceeded"])
        self.assertEqual(rc, 1, "a truncated measurement is never a green gate")

    def test_classifier_rejects_the_whole_adversarial_ref_case_list(self):
        """Same case list the ADR-163 contention probe uses (codex r1 F8)."""
        for bogus in (0, -1, 0.0, -1.0, True, False, "-1", None, float("nan"), float("-inf")):
            label, rel_ok, ref_valid = MOD._classify_entry(
                hook_p50=_HOOK_BASELINE_MS,
                hook_p95=_HOOK_BASELINE_MS,
                ref_p50=bogus,
                ref_drift=1.0,
                p95_ceiling_ms=180.0,
                k_e=_K_UNDER_TEST,
            )
            self.assertEqual(label, "infrastructure_contended", repr(bogus))
            self.assertIsNone(rel_ok, repr(bogus))
            self.assertFalse(ref_valid, repr(bogus))
        self.assertFalse(MOD._is_real_number(True))
        self.assertFalse(MOD._is_real_number("-1"))
        self.assertTrue(MOD._is_real_number(0))

    def test_wall_exceeded_short_circuits_the_classifier(self):
        label, rel_ok, ref_valid = MOD._classify_entry(
            hook_p50=1.0,
            hook_p95=1.0,
            ref_p50=1.0,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=_K_UNDER_TEST,
            wall_exceeded=True,
        )
        self.assertEqual(label, "infrastructure_contended")
        self.assertIsNone(rel_ok)
        self.assertFalse(ref_valid)

    def test_split_half_drift_is_infinite_when_undefined(self):
        self.assertEqual(MOD._split_half_drift([]), float("inf"))
        self.assertEqual(MOD._split_half_drift([1.0, 2.0]), float("inf"))
        self.assertEqual(MOD._split_half_drift([0.0, 0.0, 5.0, 5.0]), float("inf"))


# ---------------------------------------------------------------------------
# (d) the green case
# ---------------------------------------------------------------------------


class TestPassCase(TestEnvContext):
    def test_phase2_pass_exits_zero_with_expected_ratio(self):
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}),
                ],
                _Sampler(),
            )
        for name in _CORPUS_NAMES:
            stats = report["hooks"][name]
            self.assertEqual(stats["verdict_label"], "pass", name)
            self.assertIs(stats["rel_ok"], True, name)
            self.assertEqual(stats["phase"], "2-enforcing", name)
            self.assertAlmostEqual(
                stats["R_e"], _HOOK_BASELINE_MS / _REF_BASELINE_MS, places=3
            )
            self.assertEqual(stats["ref_p50_ms"], _REF_BASELINE_MS)
            self.assertEqual(stats["ref_samples"], MOD._REF_SAMPLES_PER_ENTRY)
        self.assertEqual(report["verdict_label"], "pass")
        self.assertEqual(rc, 0)
        self.assertNotIn("::warning::hook latency AMNESTY", report["_stderr"])

    def test_phase1_pass_matches_todays_exit(self):
        rc_today, _ = _run_cli([], _Sampler())
        rc_phase1, report = _run_cli(
            ["--exec-reference", "--relative-advisory"], _Sampler()
        )
        self.assertEqual(rc_today, 0)
        self.assertEqual(rc_phase1, 0)
        self.assertEqual(report["hooks"][_HEAVY]["verdict_label"], "pass")
        self.assertEqual(report["hooks"][_HEAVY]["phase"], "1-advisory")

    def test_abs_ok_but_rel_ko_is_a_pass_unless_strict(self):
        """The declared blind spot cell — implemented, tested, NOT armed."""
        common = dict(
            hook_p50=170.0,
            hook_p95=175.0,
            ref_p50=_REF_BASELINE_MS,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=_K_UNDER_TEST,
        )
        label, rel_ok, _ = MOD._classify_entry(**common)
        self.assertEqual(label, "pass")
        self.assertIs(rel_ok, False)
        strict_label, strict_rel, _ = MOD._classify_entry(strict_relative=True, **common)
        self.assertEqual(strict_label, "real_regression")
        self.assertIs(strict_rel, False)


# ---------------------------------------------------------------------------
# (e) back-compat: byte-identical without the new flags
# ---------------------------------------------------------------------------


class TestBackCompatByteIdentity(TestEnvContext):
    @staticmethod
    def _strip(report: Dict[str, Any]) -> Dict[str, Any]:
        out = json.loads(json.dumps(report))
        for key in MOD._SECOND_KEY_REPORT_KEYS:
            out.pop(key, None)
        for stats in out.get("hooks", {}).values():
            if isinstance(stats, dict):
                for key in MOD._SECOND_KEY_ENTRY_KEYS:
                    stats.pop(key, None)
        if isinstance(out.get("check_agent_spawn"), dict):
            for key in MOD._SECOND_KEY_ENTRY_KEYS:
                out["check_agent_spawn"].pop(key, None)
        out.pop("measured_at", None)
        return out

    def test_report_and_exit_are_identical_once_new_keys_are_removed(self):
        rc_old, old = _run_cli([], _Sampler())
        rc_new, new = _run_cli(
            ["--exec-reference", "--relative-advisory"], _Sampler()
        )
        old.pop("_stderr", None)
        old.pop("_stdout", None)
        new.pop("_stderr", None)
        new.pop("_stdout", None)
        self.assertEqual(rc_old, rc_new)
        self.assertEqual(
            json.dumps(self._strip(old), sort_keys=True),
            json.dumps(self._strip(new), sort_keys=True),
        )

    def test_no_flags_emits_zero_new_keys(self):
        report = _run(_Sampler())
        for key in MOD._SECOND_KEY_REPORT_KEYS:
            self.assertNotIn(key, report, "%s leaked into a no-flags report" % key)
        for name, stats in report["hooks"].items():
            for key in MOD._SECOND_KEY_ENTRY_KEYS:
                self.assertNotIn(key, stats, "%s leaked into %s" % (key, name))

    def test_every_added_key_is_registered(self):
        """Anti-rot: a future key added without registering it turns RED."""
        old = _run(_Sampler())
        with tempfile.TemporaryDirectory() as td:
            new = _run(
                _Sampler(),
                exec_reference=True,
                relative_advisory=True,
                relative_k_source=_k_file(
                    td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}
                ),
            )
        self.assertEqual(
            set(new) - set(old),
            set(MOD._SECOND_KEY_REPORT_KEYS),
            "report keys added by the second key must all be registered in "
            "_SECOND_KEY_REPORT_KEYS",
        )
        for name in _CORPUS_NAMES:
            self.assertEqual(
                set(new["hooks"][name]) - set(old["hooks"][name]),
                set(MOD._SECOND_KEY_ENTRY_KEYS),
                "%s: entry keys must all be registered in "
                "_SECOND_KEY_ENTRY_KEYS" % name,
            )

    def test_existing_defaults_are_untouched(self):
        import inspect

        sig = inspect.signature(MOD.run_hook_latency)
        self.assertEqual(sig.parameters["iterations"].default, 200)
        self.assertEqual(sig.parameters["p95_ceiling_ms"].default, 180.0)
        self.assertEqual(sig.parameters["p99_ceiling_ms"].default, 160.0)
        self.assertFalse(sig.parameters["p99_advisory"].default)
        self.assertFalse(sig.parameters["exec_reference"].default)
        self.assertFalse(sig.parameters["relative_advisory"].default)
        self.assertIsNone(sig.parameters["relative_k_source"].default)
        self.assertEqual(sig.parameters["wall_budget_seconds"].default, 420.0)
        self.assertFalse(sig.parameters["strict_relative"].default)

    def test_fail_marker_survives_for_the_shell_proofs(self):
        """`wave2-regression-proof.sh` greps this literal."""
        _rc, report = _run_cli(
            ["--exec-reference", "--relative-advisory"],
            _Sampler(hook={_HEAVY: 400.0, "*": _HOOK_BASELINE_MS}),
        )
        self.assertIn("FAIL: hook latency gate —", report["_stderr"])


# ---------------------------------------------------------------------------
# (g) env scrub — the real measurement path
# ---------------------------------------------------------------------------


class TestEnvScrub(TestEnvContext):
    """CLAUDE_PROJECT_DIR_NATIVE must never reach a measured subprocess.

    It is the highest-precedence runtime-state carrier: left in the env it
    overrides both HOME and CEO_AUDIT_LOG_DIR, and every measured hook would
    append to the LIVE HMAC chain (the S321/S326 non-attributable-elos
    class). This test uses the REAL measurement path with ``subprocess.run``
    mocked, so it inspects exactly what the profiler hands the kernel.
    """

    def _capture_envs(self, **kwargs: Any) -> List[Dict[str, str]]:
        seen: List[Dict[str, str]] = []

        def _record(*_a: Any, **kw: Any):
            seen.append(dict(kw.get("env") or {}))
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        leak = {
            "CLAUDE_PROJECT_DIR_NATIVE": "/ambient/leak",
            "CEO_LEARNING_OBSERVE": "1",
            "CLAUDE_SESSION_ID": "ambient-session",
        }
        with mock.patch.dict(os.environ, leak, clear=False):
            self.assertEqual(
                os.environ.get("CLAUDE_PROJECT_DIR_NATIVE"),
                "/ambient/leak",
                "control: the carrier really is in the ambient env",
            )
            with mock.patch.object(MOD.subprocess, "run", side_effect=_record):
                _run(None, **kwargs)
        return seen

    def test_carrier_is_absent_from_every_measured_env(self):
        seen = self._capture_envs(exec_reference=True, relative_advisory=True)
        self.assertTrue(seen, "expected subprocess invocations")
        for env in seen:
            self.assertNotIn("CLAUDE_PROJECT_DIR_NATIVE", env)
            self.assertNotIn("CLAUDE_SESSION_ID", env)
            # Plumbing control: the env really is the profiler's, not a stub.
            self.assertEqual(env.get("CEO_MODEL_ROUTING"), "0")
            self.assertTrue(env.get("HOME", "").endswith("home"))

    def test_scrub_holds_without_the_new_flags_too(self):
        for env in self._capture_envs():
            self.assertNotIn("CLAUDE_PROJECT_DIR_NATIVE", env)

    def test_reference_env_drops_pythonpath(self):
        """The reference must not even be ABLE to import the hook tree."""
        seen = self._capture_envs(exec_reference=True, relative_advisory=True)
        without_pythonpath = [e for e in seen if "PYTHONPATH" not in e]
        with_pythonpath = [e for e in seen if "PYTHONPATH" in e]
        self.assertTrue(with_pythonpath, "hook envs must carry PYTHONPATH")
        self.assertEqual(
            len(without_pythonpath),
            MOD._REF_SAMPLES_PER_ENTRY * len(_CORPUS_NAMES),
            "exactly the reference invocations run without PYTHONPATH",
        )


# ---------------------------------------------------------------------------
# (h) a K file that does not cover every entry
# ---------------------------------------------------------------------------


class TestPartialAndMalformedKSource(TestEnvContext):
    def test_entry_without_k_warns_and_stays_on_phase_1(self):
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, {"check_agent_spawn": {"K": _K_UNDER_TEST}}),
                ],
                _Sampler(hook={_HEAVY: _HOOK_BASELINE_MS + 150.0, "*": _HOOK_BASELINE_MS}),
            )
        covered = report["hooks"]["check_agent_spawn"]
        uncovered = report["hooks"][_HEAVY]
        self.assertEqual(covered["phase"], "2-enforcing")
        self.assertIs(covered["rel_ok"], True)
        self.assertEqual(uncovered["phase"], "1-advisory")
        self.assertIsNone(uncovered["K_e"])
        self.assertIsNone(uncovered["rel_ok"])
        self.assertEqual(uncovered["verdict_label"], "real_regression")
        warnings = "\n".join(report["relative_warnings"])
        self.assertIn("relative_k_missing[%s]" % _HEAVY, warnings)
        self.assertIn("WARN: relative_k_missing", report["_stderr"])
        self.assertEqual(rc, 1)

    def test_inadmissible_k_is_rejected_not_honoured(self):
        with tempfile.TemporaryDirectory() as td:
            path = _k_file(
                td,
                {n: {"K": 9.0, "admissibility_max_K": 3.0} for n in _CORPUS_NAMES},
            )
            entries, warnings = MOD._load_relative_k_source(path)
        self.assertEqual(entries, {})
        self.assertTrue(any("relative_k_inadmissible" in w for w in warnings))

    def test_bogus_k_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = _k_file(
                td,
                {
                    "a": {"K": True},
                    "b": {"K": "1.5"},
                    "c": {"K": -1},
                    "d": {"K": 0},
                    "e": {},
                    "f": {"K": 2.0},
                },
            )
            entries, warnings = MOD._load_relative_k_source(path)
        self.assertEqual(entries, {"f": 2.0})
        self.assertEqual(len(warnings), 5)

    def test_unreadable_source_degrades_to_phase_1_without_echoing_paths(self):
        with tempfile.TemporaryDirectory() as td:
            missing = str(Path(td) / "nope.json")
            entries, warnings = MOD._load_relative_k_source(missing)
        self.assertEqual(entries, {})
        self.assertEqual(len(warnings), 1)
        self.assertIn("relative_k_source_unreadable", warnings[0])
        self.assertNotIn(td, warnings[0], "no machine path may reach the report")

    def test_k_source_without_exec_reference_is_ignored_with_a_warning(self):
        with tempfile.TemporaryDirectory() as td:
            report = _run(
                _Sampler(),
                relative_advisory=True,
                relative_k_source=_k_file(
                    td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}
                ),
            )
        self.assertEqual(report["phase"], "1-advisory")
        self.assertTrue(
            any("relative_k_source_ignored" in w for w in report["relative_warnings"])
        )
        self.assertIsNone(report["hooks"][_HEAVY]["rel_ok"])


# ---------------------------------------------------------------------------
# Report hygiene
# ---------------------------------------------------------------------------


class TestReportHygiene(TestEnvContext):
    def test_no_machine_paths_in_the_relative_surface(self):
        with tempfile.TemporaryDirectory() as td:
            report = _run(
                _Sampler(),
                exec_reference=True,
                relative_advisory=True,
                relative_k_source=_k_file(
                    td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}
                ),
            )
        surface = {k: report[k] for k in MOD._SECOND_KEY_REPORT_KEYS if k in report}
        surface["hooks"] = report["hooks"]
        blob = json.dumps(surface)
        self.assertNotIn(str(_REPO), blob)
        self.assertNotIn(td, blob)
        self.assertNotIn(os.path.expanduser("~"), blob)

    def test_report_is_json_serialisable_with_an_invalid_reference(self):
        """inf/NaN must never reach the JSON (they are not valid JSON)."""
        report = _run(_Sampler(ref=0.0), exec_reference=True, relative_advisory=True)
        blob = json.dumps(report, allow_nan=False)
        self.assertNotIn("Infinity", blob)
        self.assertIsNone(report["hooks"][_HEAVY]["ref_split_half_drift"])


class TestAFailedReferenceIsNotAMeasurement(TestEnvContext):
    """rail round-1 P1 — the reference's RETURN CODE decides, not its shape.

    `_run_ref` discarded the completed process. A reference that dies on an
    import, a missing dir or a permission returns in ~15ms, repeatably — so
    it produces a finite, positive, low-drift ref_p50 that passes every
    shape test the classifier had. The gate then reads a healthy reference
    where there was none.

    The consequence lands in phase 2, where K_e is pinned from
    max(hook_p50 / ref_p50): a tiny ref_p50 pins K enormous, and an enormous
    K grants blanket amnesty on every later run.
    """

    def test_the_classifier_rejects_a_failed_reference_outright(self):
        """UNIT — healthy NUMBERS, failed PROCESS, verdict contended."""
        label, rel_ok, ref_valid = MOD._classify_entry(
            hook_p50=_HOOK_BASELINE_MS,
            hook_p95=_HOOK_BASELINE_MS,
            ref_p50=_REF_BASELINE_MS,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=_K_UNDER_TEST,
            ref_failed=True,
        )
        self.assertEqual(label, "infrastructure_contended")
        self.assertIsNone(rel_ok)
        self.assertIs(ref_valid, False)

    def test_anti_vacuity_the_same_numbers_pass_when_the_process_did_not_fail(self):
        """The twin. Without it the assertion above could be measuring
        anything — these inputs must be a PASS on their own."""
        label, rel_ok, ref_valid = MOD._classify_entry(
            hook_p50=_HOOK_BASELINE_MS,
            hook_p95=_HOOK_BASELINE_MS,
            ref_p50=_REF_BASELINE_MS,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=_K_UNDER_TEST,
            ref_failed=False,
        )
        self.assertEqual(label, "pass")
        self.assertIs(ref_valid, True)

    def test_a_real_nonzero_reference_process_reaches_the_verdict(self):
        """INTEGRATION — no sampler, so the actual subprocess lane runs.

        The unit test above pins the classifier; this one pins the WIRING
        (return code -> entry_ref_failed -> classifier -> report), which is
        the half the sampler cannot exercise: the injected lane returns a
        float and never spawns anything.
        """
        failing = "import sys\nsys.exit(1)\n"
        with mock.patch.object(MOD, "_REF_EXEC_SOURCE", failing):
            report = _run(
                None,
                exec_reference=True,
                relative_advisory=True,
                iterations=_ITERATIONS,
            )
        for name in _CORPUS_NAMES:
            stats = report["hooks"][name]
            self.assertIs(stats["ref_failed"], True, name)
            self.assertIs(stats["ref_valid"], False, name)
            self.assertEqual(stats["verdict_label"], "infrastructure_contended", name)

    def test_anti_vacuity_the_shipped_reference_exits_zero(self):
        """Control for the control: the REAL reference does NOT fail.

        Without this, the integration test above would still be green if
        every reference run failed for some unrelated reason.
        """
        report = _run(
            None,
            exec_reference=True,
            relative_advisory=True,
            iterations=_ITERATIONS,
        )
        for name in _CORPUS_NAMES:
            self.assertIs(report["hooks"][name]["ref_failed"], False, name)


class TestAKFileMayOnlyNameRealEntries(TestEnvContext):
    """rail round-1 P2 — one typo must not arm phase 2 for the whole run.

    `any_enforced` keys on `bool(k_by_entry)`. A K file naming only
    `check_output_secrets[observe=one]` left that dict non-empty while every
    real entry classified with `k_e=None` — so the run switched to the
    phase-2 exit map having applied K to nothing.
    """

    def test_an_unknown_name_is_dropped_and_named(self):
        with tempfile.TemporaryDirectory() as td:
            report = _run(
                _Sampler(),
                exec_reference=True,
                relative_advisory=True,
                relative_k_source=_k_file(td, {"no_such_entry": {"K": 99.0}}),
            )
        self.assertEqual(report["phase"], "1-advisory")
        self.assertTrue(
            any(
                w.startswith("relative_k_unknown_entry[no_such_entry]")
                for w in report["relative_warnings"]
            ),
            "the rejection must be NAMED: %r" % (report["relative_warnings"],),
        )

    def test_a_typo_only_k_file_keeps_todays_failing_exit(self):
        """THE HOLE. An absolute breach exits 1 under phase 1; with the typo
        arming phase 2 it aggregated to 'pass' and exited 0."""
        sampler = _Sampler(hook=400.0, ref=_REF_BASELINE_MS)
        with tempfile.TemporaryDirectory() as td:
            rc, report = _run_cli(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, {"no_such_entry": {"K": 99.0}}),
                ],
                sampler,
            )
        self.assertEqual(report["phase"], "1-advisory")
        self.assertEqual(rc, 1)

    def test_anti_vacuity_a_known_name_still_arms_phase_2(self):
        """The filter drops UNKNOWN names only — it must not eat real ones."""
        with tempfile.TemporaryDirectory() as td:
            report = _run(
                _Sampler(),
                exec_reference=True,
                relative_advisory=True,
                relative_k_source=_k_file(
                    td,
                    {
                        _HEAVY: {"K": _K_UNDER_TEST},
                        "no_such_entry": {"K": 99.0},
                    },
                ),
            )
        self.assertEqual(report["phase"], "2-enforcing")
        self.assertEqual(report["hooks"][_HEAVY]["K_e"], _K_UNDER_TEST)


class TestTheWallIsCheckedEveryIteration(TestEnvContext):
    """rail round-1 P2 — the self-cap must not be able to overshoot.

    The stride was `i % 10 == 0`. One iteration can spend 10s in the seed,
    10s in the hook and 10s in the reference, so a check passing just under
    the 378s deadline could be followed by ~300s unchecked — long enough for
    the outer 420s timeout to kill the process before the structured
    wall-capped result is emitted, which is the exact rc124 the cap exists
    to make unreachable.

    Asserting `wall_exceeded` alone would be VACUOUS: it was already True
    before the cure. The discriminator is HOW MANY samples were taken after
    the clock blew past the deadline — 10 with the stride, 1 without it.
    """

    @staticmethod
    def _clock_that_blows_after(n_calls: int):
        """perf_counter stub: normal for `n_calls`, then far past any wall."""
        state = {"n": 0}

        def _clock() -> float:
            state["n"] += 1
            return 0.0 if state["n"] <= n_calls else 10_000.0

        return _clock

    def test_sampling_stops_within_one_iteration_of_the_deadline(self):
        # Calls 1 and 2 are `t_gate_start` and the per-ENTRY check at the top
        # of the corpus loop; both must read normal or no entry is measured
        # at all and the test would prove nothing.
        sampler = _Sampler()
        with mock.patch.object(
            MOD.time, "perf_counter", self._clock_that_blows_after(2)
        ):
            report = _run(sampler, exec_reference=True, relative_advisory=True)
        first_entry = _CORPUS_NAMES[0]
        warm = [c for c in sampler.calls if c[0] == first_entry and c[1] == "warm"]
        self.assertTrue(report["wall_exceeded"])
        self.assertEqual(
            len(warm), 1,
            "the wall must be re-read before the reference lane of the SAME "
            "iteration; %d warm samples means a stride is back" % len(warm),
        )

    def test_anti_vacuity_a_healthy_clock_runs_the_whole_corpus(self):
        """Control: with a normal clock nothing is wall-capped."""
        sampler = _Sampler()
        report = _run(sampler, exec_reference=True, relative_advisory=True)
        first_entry = _CORPUS_NAMES[0]
        warm = [c for c in sampler.calls if c[0] == first_entry and c[1] == "warm"]
        self.assertFalse(report["wall_exceeded"])
        self.assertEqual(len(warm), _ITERATIONS)


class TestAReferenceTimeoutIsAlsoAFailedMeasurement(TestEnvContext):
    """rail round-2 P2 — the other half of the round-1 P1 cure.

    The round-1 cure marked a non-zero RETURN CODE. A reference that hangs
    and is killed at 10s was left to "poison ref_p50/drift" on its own. It
    does not, and the reason is structural: the gate keys on the MEDIAN
    precisely because the median is robust to a minority of outliers
    (ADR-163:258), so a handful of dead reference processes cannot move it.
    """

    def test_a_minority_of_timeouts_does_not_move_the_median(self):
        """The REFUTATION, run against the module's own functions.

        This is the measurement that makes the cure necessary — without it
        the change reads as belt-and-braces instead of a closed hole.
        """
        samples = [_REF_BASELINE_MS] * MOD._REF_SAMPLES_PER_ENTRY
        for i in (5, 18, 33):
            samples[i] = 10_000.0
        ref_p50 = MOD._pct_of_sorted(sorted(samples), 50)
        drift = MOD._split_half_drift(samples)
        self.assertEqual(ref_p50, _REF_BASELINE_MS)
        self.assertLessEqual(drift, MOD._REF_DRIFT_MAX)
        label, _rel_ok, ref_valid = MOD._classify_entry(
            hook_p50=_HOOK_BASELINE_MS,
            hook_p95=_HOOK_BASELINE_MS,
            ref_p50=ref_p50,
            ref_drift=drift,
            p95_ceiling_ms=180.0,
            k_e=_K_UNDER_TEST,
        )
        self.assertEqual(
            label, "pass",
            "if the shape checks caught diluted timeouts on their own, the "
            "explicit ref_failed flag would be unnecessary",
        )
        self.assertIs(ref_valid, True)

    def test_a_timing_out_reference_process_reads_contended(self):
        """INTEGRATION — a reference that never returns marks the entry."""
        hanging = "import time\ntime.sleep(3600)\n"
        with mock.patch.object(MOD, "_REF_EXEC_SOURCE", hanging):
            with mock.patch.object(MOD.subprocess, "run", _timeout_on_ref()):
                report = _run(
                    None,
                    exec_reference=True,
                    relative_advisory=True,
                    iterations=_ITERATIONS,
                )
        for name in _CORPUS_NAMES:
            stats = report["hooks"][name]
            self.assertIs(stats["ref_failed"], True, name)
            self.assertEqual(stats["verdict_label"], "infrastructure_contended", name)


def _timeout_on_ref():
    """`subprocess.run` that raises TimeoutExpired for the REFERENCE only.

    Sleeping for real would cost 10s per sample. The corpus hooks must keep
    running normally, otherwise the run fails as a hook failure and the
    reference verdict under test never gets reached.
    """
    real = MOD.subprocess.run

    def _run_or_timeout(cmd, **kwargs):
        if any("ref_exec" in str(part) for part in cmd):
            raise MOD.subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 10))
        return real(cmd, **kwargs)

    return _run_or_timeout


class TestTheHardP99CeilingSurvivesPhase2(TestEnvContext):
    """rail round-2 P2 — arming phase 2 must not drop a documented ceiling.

    `_classify_entry` keys the absolute half on p95 alone. An entry that
    meets p95 and the relative key but breaches the hard p99 ceiling is
    labelled "pass", and the phase-2 branch mapped that label straight to
    exit 0 — so switching a K file on silently retired the p99 contract that
    phase 1 still enforces.
    """

    @staticmethod
    def _p99_breaching_hook():
        """p95 comfortably inside, p99 outside: only the top sample is huge.

        With `_ITERATIONS=22` the nearest-rank indices are p95 -> sorted[19]
        and p99 -> sorted[20], so TWO large samples are needed: they occupy
        sorted[20] and sorted[21], lifting p99 while leaving p95 at the
        baseline. (One is not enough — it lands on sorted[21] alone and p99
        stays inside, which is what the anti-vacuity test below pins.)
        """
        def _hook(entry: str, index: int) -> float:
            return 400.0 if index >= 20 else _HOOK_BASELINE_MS
        return _hook

    def _report(self, argv_tail: List[str]):
        sampler = _Sampler(hook=self._p99_breaching_hook(), ref=_REF_BASELINE_MS)
        return _run_cli(argv_tail, sampler)

    def test_the_fixture_really_separates_p95_from_p99(self):
        """Anti-vacuity: without this the two tests below could be measuring
        an ordinary p95 breach and prove nothing about p99."""
        rc, report = self._report(["--exec-reference", "--relative-advisory"])
        stats = report["hooks"][_HEAVY]
        self.assertLessEqual(stats["p95_ms"], 180.0)
        self.assertIs(stats["p99_within"], False)
        self.assertEqual(rc, 1)

    def test_phase2_still_exits_1_on_a_hard_p99_breach(self):
        with tempfile.TemporaryDirectory() as td:
            rc, report = self._report(
                [
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}),
                ]
            )
        self.assertEqual(report["phase"], "2-enforcing")
        self.assertEqual(
            rc, 1,
            "a hard p99 breach must survive phase 2; label was %r"
            % report["verdict_label"],
        )

    def test_p99_advisory_still_lets_phase2_exit_zero(self):
        """The ceiling is HARD only when it is hard — `--p99-advisory` is
        the CI gate's mode and must keep granting exit 0."""
        with tempfile.TemporaryDirectory() as td:
            rc, report = self._report(
                [
                    "--p99-advisory",
                    "--exec-reference",
                    "--relative-advisory",
                    "--relative-k-source",
                    _k_file(td, {n: {"K": _K_UNDER_TEST} for n in _CORPUS_NAMES}),
                ]
            )
        self.assertEqual(report["phase"], "2-enforcing")
        self.assertEqual(rc, 0)


class TestTheAdmissibilityCapIsExclusive(TestEnvContext):
    """rail round-3 P2 — K landing exactly ON the cap loses the control.

    `admissibility_max_K` encodes one guarantee: at the worst observed
    reference, a +150ms regression still FAILS. Detection needs
    `hook_p50 > K * ref_p50`, so K must be STRICTLY below
    (baseline+150)/max_ref — the classifier's comparison is inclusive.
    """

    _BASE = _HOOK_BASELINE_MS
    _REF = _REF_BASELINE_MS
    _CAP = (_HOOK_BASELINE_MS + 150.0) / _REF_BASELINE_MS
    _REGRESSED = _HOOK_BASELINE_MS + 150.0

    def test_the_boundary_really_loses_the_positive_control(self):
        """The MEASUREMENT the cure rests on, as an executable claim.

        If K==cap detected the regression on its own, rejecting equality
        would be pointless tightening.
        """
        label_at, rel_at, _ = MOD._classify_entry(
            hook_p50=self._REGRESSED,
            hook_p95=self._REGRESSED,
            ref_p50=self._REF,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=self._CAP,
        )
        label_below, rel_below, _ = MOD._classify_entry(
            hook_p50=self._REGRESSED,
            hook_p95=self._REGRESSED,
            ref_p50=self._REF,
            ref_drift=1.0,
            p95_ceiling_ms=180.0,
            k_e=self._CAP * 0.999,
        )
        self.assertEqual(label_at, "advisory_slow_runner")
        self.assertIs(rel_at, True)
        self.assertEqual(label_below, "real_regression")
        self.assertIs(rel_below, False)

    def test_k_equal_to_the_cap_is_rejected_and_named(self):
        with tempfile.TemporaryDirectory() as td:
            k_by_entry, warns = MOD._load_relative_k_source(
                _k_file(
                    td,
                    {
                        _HEAVY: {
                            "K": self._CAP,
                            "admissibility_max_K": self._CAP,
                        }
                    },
                )
            )
        self.assertEqual(k_by_entry, {})
        self.assertTrue(
            any(w.startswith("relative_k_inadmissible[%s]" % _HEAVY) for w in warns),
            "the rejection must be NAMED: %r" % (warns,),
        )

    def test_anti_vacuity_k_below_the_cap_is_still_accepted(self):
        """The cap must stay a boundary, not become a blanket rejection."""
        with tempfile.TemporaryDirectory() as td:
            k_by_entry, warns = MOD._load_relative_k_source(
                _k_file(
                    td,
                    {
                        _HEAVY: {
                            "K": self._CAP * 0.99,
                            "admissibility_max_K": self._CAP,
                        }
                    },
                )
            )
        self.assertEqual(list(k_by_entry), [_HEAVY])
        self.assertEqual(warns, [])


class TestTheTopLevelLabelNeverContradictsTheExit(TestEnvContext):
    """rail round-4 P2 — `--exec-reference` alone published a false "pass".

    That flag combination is supported and stores no per-entry
    `verdict_label` (those are gated on `relative_advisory or
    relative_k_source`), so the aggregate saw an empty list and fell back to
    the literal "pass" — in a report whose own `passed` was false and whose
    `exit_class` was 1.
    """

    @staticmethod
    def _over_ceiling():
        return _Sampler(hook=400.0, ref=_REF_BASELINE_MS)

    def test_exec_reference_only_reports_the_absolute_verdict(self):
        report = _run(self._over_ceiling(), exec_reference=True)
        self.assertIs(report["passed"], False)
        self.assertEqual(
            [
                block.get("verdict_label")
                for block in report["hooks"].values()
                if isinstance(block, dict)
            ],
            [None] * len(_CORPUS_NAMES),
            "this mode is only interesting while it stores no entry labels",
        )
        self.assertEqual(report["verdict_label"], "real_regression")
        self.assertEqual(report["exit_class"], 1)

    def test_the_label_and_the_exit_class_agree_in_this_mode(self):
        """The invariant, stated directly: exit 0 iff the label is amnesty
        or pass. A report that fails this is self-contradicting whatever the
        individual values happen to be."""
        for sampler, expect_zero in (
            (_Sampler(), True),
            (self._over_ceiling(), False),
        ):
            report = _run(sampler, exec_reference=True)
            label = report["verdict_label"]
            self.assertEqual(
                MOD._LABEL_EXIT_CLASS[label] == 0,
                expect_zero,
                "label %r disagrees with passed=%r" % (label, report["passed"]),
            )
            self.assertEqual(report["exit_class"] == 0, expect_zero)

    def test_anti_vacuity_a_healthy_run_still_reads_pass(self):
        report = _run(_Sampler(), exec_reference=True)
        self.assertIs(report["passed"], True)
        self.assertEqual(report["verdict_label"], "pass")
        self.assertEqual(report["exit_class"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
