"""test_check_model_currency.py — PLAN-176 W0a.

Covers the offline model-currency detector
(``.claude/scripts/check-model-currency.py``). Every AC of the W0a wave has a
POSITIVE control here: the property is planted-violated and the assertion goes
RED, so a green run is evidence rather than a claim.

  1. names_the_finding_and_separates_exit_codes
  2. no_network_runtime_oracle_with_transitive_import_control
  3. injected_model_turns_red
  4. state_file_contract_has_cycle_lanes_fp_and_ts
  5. state_json_serves_all_seven_death_criteria
  6. expected_reds_file_has_a_cause_per_line
  7. expected_reds_exact_set_with_shrinkage_control
  8. active_lanes_is_anthropic_only

Plus three cases from the post-refutation cure (they are not W0a ACs; they
close findings R2, R3 and R4 of the QA refuter):

  9. state_json_evaluates_thresholds_not_just_presence
 10. state_does_not_silence_the_expected_reds_gate
 11. record_cycle_advances_the_k6_streak_per_lane

Every write-path case runs in a DISPOSABLE tree (S332 lesson: a test whose
safety depends on the artifact it checks is not a test).
"""
from __future__ import annotations

import importlib.util
import io
import json
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-model-currency.py"
REAL_ADR = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
REAL_EXPECTED_REDS = (
    REPO_ROOT / ".claude" / "data" / "model-currency-expected-reds.txt")
REAL_STATE = REPO_ROOT / ".claude" / "data" / "model-currency-state.json"

#: The death criteria of PLAN-176 §4. The AC name says "seven" because §4
#: carried seven when the check was written; debate round 2 appended K-8 and
#: K-9. Asserting all NINE serves the seven a fortiori.
DEATH_CRITERIA = ("K-1", "K-2", "K-3", "K-4", "K-5", "K-6", "K-7", "K-8", "K-9")


def _load_module():
    """Load check-model-currency.py (hyphenated filename) as a module."""
    spec = importlib.util.spec_from_file_location(
        "check_model_currency", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_model_currency"] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


def run(argv):
    """Invoke main() and return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = MOD.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def run_json(argv):
    rc, out, err = run(list(argv) + ["--json"])
    return rc, json.loads(out), err


class _Fixture(TestEnvContext):
    """Builds a minimal, INTERNALLY COHERENT tree (the exit-0 baseline)."""

    WORKING_SET = ("claude-opus-4-8", "claude-fable-5")
    VETO_FLOOR = ("claude-opus-4-8", "claude-fable-5")

    def _tree(self, working_set=None, priced=None, replacements=None,
              available=None):
        root = Path(tempfile.mkdtemp(prefix="p176w0a-"))
        self.addCleanup(__import__("shutil").rmtree, root, True)
        working_set = list(
            self.WORKING_SET if working_set is None else working_set)
        priced = list(working_set if priced is None else priced)
        replacements = list(
            [working_set[0]] if replacements is None else replacements)
        available = list(working_set if available is None else available)

        adr = root / "adr.md"
        adr.write_text(
            "# synthetic ADR\n\n```python\nVETO_FLOOR_ALLOWED: frozenset ="
            " frozenset({\n%s})\n```\n\n```python\n"
            "AVAILABLE_MODELS_WORKING_SET: tuple = (\n%s)\n```\n"
            % ("".join('    "%s",\n' % m for m in self.VETO_FLOOR),
               "".join('    "%s",  # comment\n' % m for m in working_set)),
            encoding="utf-8")
        shape = root / "shape.py"
        shape.write_text(
            "from typing import Tuple\n"
            '_VALID_MODELS: Tuple[str, ...] = (\n    "gpt-5.5",\n)\n',
            encoding="utf-8")
        cost = root / "cost-table.yaml"
        cost.write_text(
            "schema_version: \"1.0\"\nmodels:\n%s\nparallel_ceiling:\n"
            "  max_parallel: 6\n"
            % "".join("  %s:\n    input: 1.0\n" % m for m in priced),
            encoding="utf-8")
        deps = root / "deps.json"
        deps.write_text(json.dumps({"models": [
            {"model_id": "claude-legacy-%d" % i, "replacement": r}
            for i, r in enumerate(replacements)]}), encoding="utf-8")
        settings = root / "settings.json"
        settings.write_text(json.dumps({
            "model": working_set[0], "availableModels": available,
            "fallbackModel": [working_set[0]]}), encoding="utf-8")
        return root, [
            "--adr", str(adr), "--codex-shape", str(shape),
            "--cost-table", str(cost), "--deprecations", str(deps),
            "--settings", str(settings)]

    def _real_argv(self, **override):
        """argv pointing at the LIVE tree, with named path overrides."""
        argv = ["--root", str(REPO_ROOT)]
        for flag, value in override.items():
            argv += ["--" + flag.replace("_", "-"), str(value)]
        return argv


class TestFindingsAndExitCodes(_Fixture):

    def test_names_the_finding_and_separates_exit_codes(self):
        # rc 0 — ran, no finding.
        _root, argv = self._tree()
        rc, report, _ = run_json(argv)
        self.assertEqual(rc, 0, report["findings"])
        self.assertEqual(report["findings"], [])

        # rc 1 — ran, one NAMED finding. POSITIVE CONTROL: the extra priced
        # id is the only difference from the green tree above.
        _root, argv = self._tree(priced=list(self.WORKING_SET) + ["claude-x-9"])
        rc, report, _ = run_json(argv)
        self.assertEqual(rc, 1)
        self.assertEqual(len(report["findings"]), 1)
        finding = report["findings"][0]
        for key in ("model_id", "surface", "authority", "kind", "lane"):
            self.assertTrue(finding[key], "finding is not named: %r" % finding)
        self.assertEqual(finding["model_id"], "claude-x-9")
        self.assertEqual(finding["surface"], "cost-table.yaml")
        self.assertEqual(
            finding["authority"], "ADR-149:AVAILABLE_MODELS_WORKING_SET")

        # rc >= 2 — the detector BROKE. A missing authority must never be
        # reported as "no finding" (0) nor as a finding (1).
        rc, _out, err = run(argv[:1] + [str(Path(argv[1]).parent / "gone.md")]
                            + argv[2:])
        self.assertGreaterEqual(rc, 2)
        self.assertIn("DETECTOR-BROKE", err)

        # rc >= 2 — an authority defined TWICE is ambiguity, not a finding.
        root, argv = self._tree()
        adr = Path(argv[1])
        adr.write_text(adr.read_text(encoding="utf-8") * 2, encoding="utf-8")
        rc, _out, err = run(argv)
        self.assertGreaterEqual(rc, 2)
        self.assertIn("expected exactly 1 definition", err)


def _socket_ban(*_args, **_kwargs):
    raise AssertionError("network primitive called under the no-network oracle")


class TestNoNetwork(_Fixture):

    def _under_socket_ban(self, call):
        """THE oracle. Both the negative and the positive control run it."""
        real_socket, real_conn = socket.socket, socket.create_connection
        socket.socket, socket.create_connection = _socket_ban, _socket_ban
        try:
            return call()
        finally:
            socket.socket, socket.create_connection = real_socket, real_conn

    def test_no_network_runtime_oracle_with_transitive_import_control(self):
        # NEGATIVE: the detector completes a full live scan under the ban.
        _root, argv = self._tree()
        rc = self._under_socket_ban(lambda: run(argv)[0])
        self.assertEqual(rc, 0)
        rc = self._under_socket_ban(
            lambda: run(self._real_argv())[0])
        self.assertIn(rc, (0, 1))

        # POSITIVE CONTROL — reproduces the MECHANISM that defeats a name
        # grep: the consumer acquires egress by TRANSITIVE IMPORT, so its own
        # source never mentions a networking primitive.
        root = Path(tempfile.mkdtemp(prefix="p176w0a-egress-"))
        self.addCleanup(__import__("shutil").rmtree, root, True)
        lib = root / "_lib"
        lib.mkdir()
        (lib / "__init__.py").write_text("", encoding="utf-8")
        (lib / "model_feed_fetch.py").write_text(
            "import socket\n\n\ndef fetch():\n"
            "    return socket.create_connection(('127.0.0.1', 9), 0.01)\n",
            encoding="utf-8")
        consumer = root / "synthetic_probe.py"
        consumer.write_text(
            "from _lib import model_feed_fetch\n\n\ndef run():\n"
            "    return model_feed_fetch.fetch()\n", encoding="utf-8")

        # The grep a text instrument would run is BLIND to this file.
        self.assertNotIn("socket", consumer.read_text(encoding="utf-8"))

        # Shadow the real `_lib` for the duration of the import so the
        # consumer's literal `from _lib import model_feed_fetch` — the exact
        # spelling W0b will offer — resolves to the synthetic package.
        real_lib = sys.modules.pop("_lib", None)
        sys.path.insert(0, str(root))
        try:
            spec = importlib.util.spec_from_file_location(
                "p176_synthetic_probe", consumer)
            probe = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(probe)
        finally:
            sys.path.remove(str(root))
            sys.modules.pop("_lib", None)
            sys.modules.pop("_lib.model_feed_fetch", None)
            if real_lib is not None:
                sys.modules["_lib"] = real_lib

        # The SAME oracle goes RED on it.
        with self.assertRaises(AssertionError):
            self._under_socket_ban(probe.run)


class TestInjectedModel(_Fixture):

    def test_injected_model_turns_red(self):
        # Baseline on the LIVE tree: the gate is GREEN against the tracked
        # expected-red set.
        rc, _out, err = run(self._real_argv(
            expected_reds=REAL_EXPECTED_REDS))
        self.assertEqual(rc, 0, err)

        # POSITIVE CONTROL: inject a model id that exists nowhere else into
        # the ADR working set, on a DISPOSABLE copy of the real ADR.
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-adr-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        copy = tmp / "ADR-149.md"
        original = REAL_ADR.read_text(encoding="utf-8")
        anchor = '    "claude-fable-5-1",'
        self.assertIn(anchor, original, "ADR-149 injection anchor moved")
        copy.write_text(
            original.replace(anchor, anchor + '\n    "claude-opus-6",', 1),
            encoding="utf-8")

        rc, report, err = run_json(self._real_argv(
            adr=copy, expected_reds=REAL_EXPECTED_REDS))
        self.assertEqual(rc, 1, err)
        self.assertIn("claude-opus-6", report["red_ids"])
        self.assertIn("claude-opus-6", report["expected_reds"]["unexpected"])
        injected = [f for f in report["findings"]
                    if f["model_id"] == "claude-opus-6"]
        self.assertEqual(len(injected), 1)
        self.assertEqual(injected[0]["kind"], "working_set_without_price")


class TestStateFile(_Fixture):

    def test_state_file_contract_has_cycle_lanes_fp_and_ts(self):
        state = json.loads(REAL_STATE.read_text(encoding="utf-8"))
        self.assertIsInstance(state["cycle"], int)
        self.assertTrue(state["lanes"])
        for lane in state["lanes"].values():
            self.assertIsInstance(lane["consecutive_failures"], int)
            self.assertIn("active", lane)
        self.assertIsInstance(state["false_positives"]["count"], int)
        self.assertIsInstance(state["false_positives"]["window_cycles"], int)
        MOD._state_age_hours(state, MOD._dt.datetime(2026, 9, 7))

        # POSITIVE CONTROL, on a DISPOSABLE copy: drop `ts` and the reader
        # fails CLOSED instead of serving an ageless state.
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-state-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        broken = tmp / "state.json"
        state.pop("ts")
        broken.write_text(json.dumps(state), encoding="utf-8")
        rc, _out, err = run(self._real_argv(state_file=broken) + ["--state"])
        self.assertGreaterEqual(rc, 2)
        self.assertIn("'ts'", err)

        # --record-cycle advances the counter — DISPOSABLE tree only.
        fresh = tmp / "fresh.json"
        fresh.write_text(REAL_STATE.read_text(encoding="utf-8"),
                         encoding="utf-8")
        rc, _out, err = run(self._real_argv(state_file=fresh)
                            + ["--record-cycle"])
        self.assertIn(rc, (0, 1), err)
        self.assertEqual(
            json.loads(fresh.read_text(encoding="utf-8"))["cycle"], 1)

    def test_state_json_serves_all_seven_death_criteria(self):
        rc, payload, err = run_json(
            self._real_argv(state_file=REAL_STATE)
            + ["--state", "--now", "2026-09-07T12:00:00Z"])
        self.assertEqual(rc, 0, err)
        served = {c["criterion"]: c for c in payload["criteria"]}
        self.assertEqual(tuple(sorted(served)), DEATH_CRITERIA)
        for name in DEATH_CRITERIA:
            entry = served[name]
            self.assertTrue(entry["field"], name)
            self.assertTrue(entry["threshold"], name)
            self.assertIn("value", entry, name)
            # The verdict must say what was MEASURED, never merely that the
            # field exists (the R2 defect: a decorative "wired" label).
            self.assertIn(entry["verdict"], ("ok", "breached", "not_yet_wired"),
                          name)
            self.assertIn(entry["enforcement"], ("fail_closed", "report_only"),
                          name)
        self.assertEqual(served["K-8"]["value"], 1)
        self.assertEqual(served["K-9"]["value"], 12.0)

        # POSITIVE CONTROL, on a DISPOSABLE copy: a criterion whose field is
        # gone must FAIL CLOSED and NAME the criterion — never quietly serve
        # eight of nine.
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-crit-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        for name, field, _threshold, _enf, _gated in MOD._DEATH_CRITERIA:
            if field.startswith("@"):
                continue
            state = json.loads(REAL_STATE.read_text(encoding="utf-8"))
            state.pop(field.split(".")[0])
            plant = tmp / ("no-%s.json" % name)
            plant.write_text(json.dumps(state), encoding="utf-8")
            rc, _out, err = run(
                self._real_argv(state_file=plant) + ["--state"])
            self.assertGreaterEqual(rc, 2, name)
            self.assertIn(name, err)

    def test_state_json_evaluates_thresholds_not_just_presence(self):
        """R2 — the §4 thresholds are APPLIED, not merely served."""
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-thresh-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)

        def _run_state(mutate, now="2026-09-07T12:00:00Z"):
            state = json.loads(REAL_STATE.read_text(encoding="utf-8"))
            mutate(state)
            plant = tmp / ("s%d.json" % len(list(tmp.iterdir())))
            plant.write_text(json.dumps(state), encoding="utf-8")
            rc, payload, err = run_json(
                self._real_argv(state_file=plant) + ["--state", "--now", now])
            return rc, {c["criterion"]: c for c in payload["criteria"]}, err

        # Baseline: the shipped state breaches nothing.
        rc, served, err = _run_state(lambda s: None)
        self.assertEqual(rc, 0, err)
        self.assertEqual(
            [n for n, c in served.items() if c["verdict"] == "breached"], [])

        # Each fail-closed criterion ALONE, at ONE occurrence, exits 2 and
        # names itself on stderr. These are the three §4 spells "qualquer
        # ocorrência" — the ones that used to exit 0 in silence.
        for field, value in (("trust_layer_touches", 1),
                             ("schema_break", True),
                             ("phase2_auto_merge_enabled", True)):
            rc, served, err = _run_state(
                lambda s, f=field, v=value: s.__setitem__(f, v))
            self.assertEqual(rc, 2, field)
            breached = [n for n, c in served.items()
                        if c["verdict"] == "breached"]
            self.assertEqual(len(breached), 1, breached)
            self.assertIn(breached[0], err)
            self.assertEqual(served[breached[0]]["enforcement"], "fail_closed")

        # Report-only criteria need the cadence, and then exit 1 (not 0, not 2).
        def _blow_report_only(state):
            state["cadence_started"] = True
            state["false_positives"]["count"] = 99
            state["upstream"] = {"present": True, "complete": False,
                                 "age_cycles": 9, "age_hours": 9999.0}
            state["false_negative_probe"]["passed"] = False
            state["lanes"]["anthropic"]["consecutive_failures"] = 77
            state["ts"] = "2020-01-01T00:00:00Z"
        rc, served, err = _run_state(_blow_report_only)
        self.assertEqual(rc, 1, err)
        for name in ("K-1", "K-3", "K-5", "K-6", "K-9"):
            self.assertEqual(served[name]["verdict"], "breached", name)
            self.assertIn(name, err)
        for name in ("K-2", "K-4", "K-7", "K-8"):
            self.assertEqual(served[name]["verdict"], "ok", name)

        # Everything blown at once: the WORST code wins, and no criterion is
        # silently reported as fine.
        def _blow_everything(state):
            _blow_report_only(state)
            state["trust_layer_touches"] = 42
            state["schema_break"] = True
            state["phase2_auto_merge_enabled"] = True
        rc, served, err = _run_state(_blow_everything)
        self.assertEqual(rc, 2, err)
        self.assertEqual(
            sorted(n for n, c in served.items() if c["verdict"] == "breached"),
            ["K-1", "K-2", "K-3", "K-4", "K-5", "K-6", "K-7", "K-9"])
        self.assertNotEqual(err.strip(), "")

    def test_state_does_not_silence_the_expected_reds_gate(self):
        """R3 — flag composition keeps the MOST SEVERE exit code."""
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-compose-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        bogus = tmp / "bogus.txt"
        bogus.write_text("# planted cause\nclaude-ghost-9\n", encoding="utf-8")

        # The gate alone is RED.
        rc_gate, _out, _err = run(self._real_argv(expected_reds=bogus))
        self.assertEqual(rc_gate, 1)
        # --state alone is GREEN on the shipped state.
        rc_state, _out, _err = run(
            self._real_argv(state_file=REAL_STATE) + ["--state"])
        self.assertEqual(rc_state, 0)
        # Composed: the gate must NOT be silenced.
        rc_both, payload, err = run_json(
            self._real_argv(state_file=REAL_STATE, expected_reds=bogus)
            + ["--state"])
        self.assertEqual(rc_both, 1, err)
        # The composed run still carries the gate's verdict, both in the
        # payload and on stderr — it is not merely a non-zero code.
        observed = run_json(self._real_argv())[1]["red_ids"]
        self.assertEqual(payload["expected_reds"]["unexpected"], observed)
        self.assertEqual(payload["expected_reds"]["missing"],
                         ["claude-ghost-9"])
        self.assertIn("RED-SET", err)
        # And a fail-closed criterion still wins over the gate's 1.
        broken = tmp / "broken.json"
        state = json.loads(REAL_STATE.read_text(encoding="utf-8"))
        state["trust_layer_touches"] = 1
        broken.write_text(json.dumps(state), encoding="utf-8")
        rc_worst, _payload, _err = run_json(
            self._real_argv(state_file=broken, expected_reds=bogus)
            + ["--state"])
        self.assertEqual(rc_worst, 2)

    def test_record_cycle_advances_the_k6_streak_per_lane(self):
        """R4 — K-6's counter is not structurally frozen."""
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-streak-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        plant = tmp / "state.json"
        plant.write_text(REAL_STATE.read_text(encoding="utf-8"),
                         encoding="utf-8")
        for expected in (1, 2, 3):
            run(self._real_argv(state_file=plant) + ["--record-cycle"])
            lanes = json.loads(plant.read_text(encoding="utf-8"))["lanes"]
            # The live tree has anthropic findings every run, so the streak
            # ADVANCES — the old code wrote the seed value back forever.
            self.assertEqual(lanes["anthropic"]["consecutive_failures"],
                             expected)
            # The INERT lane never inherits someone else's finding.
            self.assertEqual(lanes["openai"]["result"], "inert")
            self.assertEqual(lanes["openai"]["consecutive_failures"], 0)
        # At 3 the K-6 threshold is crossed and --state reports it.
        state = json.loads(plant.read_text(encoding="utf-8"))
        state["cadence_started"] = True
        plant.write_text(json.dumps(state), encoding="utf-8")
        rc, payload, err = run_json(
            self._real_argv(state_file=plant)
            + ["--state", "--now", "2026-09-07T12:00:00Z"])
        served = {c["criterion"]: c for c in payload["criteria"]}
        self.assertEqual(served["K-6"]["verdict"], "breached", err)
        self.assertEqual(rc, 1)


class TestExpectedReds(_Fixture):

    def test_expected_reds_file_has_a_cause_per_line(self):
        lines = REAL_EXPECTED_REDS.read_text(encoding="utf-8").splitlines()
        ids, preceding_comments, seen_any = [], 0, False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                preceding_comments += 1
                continue
            if not stripped:
                continue
            seen_any = True
            self.assertGreater(
                preceding_comments, 0,
                "id %r has no cause comment above it" % stripped)
            ids.append(stripped)
            preceding_comments = 0
        self.assertTrue(seen_any)
        self.assertEqual(len(ids), len(set(ids)), "duplicate id")
        self.assertEqual(sorted(ids), MOD.read_expected_reds(
            REAL_EXPECTED_REDS))

        # POSITIVE CONTROL: a bare id with no cause above it is REJECTED by
        # the same walk, on a DISPOSABLE copy.
        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-reds-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        plant = tmp / "reds.txt"
        plant.write_text("# cause\nclaude-a\nclaude-b\n", encoding="utf-8")
        uncaused = []
        comments = 0
        for line in plant.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#"):
                comments += 1
                continue
            if line.strip():
                if comments == 0:
                    uncaused.append(line.strip())
                comments = 0
        self.assertEqual(uncaused, ["claude-b"])

    def test_expected_reds_exact_set_with_shrinkage_control(self):
        rc, report, err = run_json(
            self._real_argv(expected_reds=REAL_EXPECTED_REDS))
        self.assertEqual(rc, 0, err)
        self.assertEqual(report["expected_reds"]["unexpected"], [])
        self.assertEqual(report["expected_reds"]["missing"], [])
        observed = list(report["red_ids"])
        self.assertEqual(len(observed), 7, observed)

        tmp = Path(tempfile.mkdtemp(prefix="p176w0a-exact-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        body = REAL_EXPECTED_REDS.read_text(encoding="utf-8")

        # POSITIVE CONTROL A — one id MORE than reality (SHRINKAGE: a red the
        # file expects that the tree no longer produces).
        more = tmp / "more.txt"
        more.write_text(body + "# planted\nclaude-ghost-7\n", encoding="utf-8")
        rc, report, err = run_json(self._real_argv(expected_reds=more))
        self.assertEqual(rc, 1, err)
        self.assertEqual(report["expected_reds"]["missing"], ["claude-ghost-7"])
        self.assertIn("shrinkage", err.lower())

        # POSITIVE CONTROL B — one id LESS than reality.
        dropped = observed[0]
        less = tmp / "less.txt"
        less.write_text(
            "\n".join(l for l in body.splitlines() if l.strip() != dropped)
            + "\n", encoding="utf-8")
        rc, report, err = run_json(self._real_argv(expected_reds=less))
        self.assertEqual(rc, 1, err)
        self.assertEqual(report["expected_reds"]["unexpected"], [dropped])


class TestActiveLanes(_Fixture):

    def test_active_lanes_is_anthropic_only(self):
        rc, report, err = run_json(self._real_argv())
        self.assertIn(rc, (0, 1), err)
        self.assertEqual(report["active_lanes"], ["anthropic"])
        self.assertTrue(report["lanes"]["anthropic"]["active"])
        self.assertFalse(report["lanes"]["openai"]["active"])
        self.assertEqual(report["lanes"]["openai"]["priced_rows"], 0)

        # POSITIVE CONTROL — the lane is DERIVED, not hardcoded. Price ONLY a
        # foreign-family id: anthropic keeps working-set members but loses
        # every priced row, openai keeps a priced row but has no working-set
        # member, so BOTH lanes go inert. K-8 makes that a fail-CLOSED break
        # instead of a green-empty run.
        _root, argv = self._tree(priced=["gpt-5.5"])
        rc, _out, err = run(argv)
        self.assertGreaterEqual(rc, 2)
        self.assertIn("K-8", err)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
