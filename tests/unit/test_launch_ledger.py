"""Unit tests for ``_lib/launch_ledger.py`` (PLAN-190 W1, v6) — pure functions and
the on-disk index, in a temp ledger dir (no resolver, no live ~/.claude)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve()
while not (_REPO / ".claude").is_dir() or not (_REPO / "VERSION").is_file():
    if _REPO.parent == _REPO:
        raise RuntimeError("repo root not found")
    _REPO = _REPO.parent
sys.path.insert(0, str(_REPO / ".claude" / "hooks"))
from _lib import launch_ledger as LL  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class ArgsScriptAndIds(TestEnvContext):
    def test_absent_null_and_empty_are_three_distinct_records(self):
        absent = LL.args_record({})
        null = LL.args_record({"args": None})
        empty = LL.args_record({"args": {}})
        self.assertFalse(absent["present"])
        self.assertEqual(absent["canonical"], LL.ABSENT)
        self.assertEqual(null["canonical"], "null")
        self.assertEqual(empty["canonical"], "{}")
        self.assertEqual(len({absent["sha256"], null["sha256"], empty["sha256"]}), 3)

    def test_canonical_json_is_key_order_independent_and_never_truncated(self):
        a = LL.args_record({"args": {"b": 1, "a": [1, 2]}})
        b = LL.args_record({"args": {"a": [1, 2], "b": 1}})
        self.assertEqual(a["canonical"], b["canonical"])
        big = LL.args_record({"args": {"x": "y" * 6_000_000}})
        self.assertEqual(big["bytes"], len(big["canonical"].encode("utf-8")))
        self.assertEqual(json.loads(big["canonical"])["x"][:3], "yyy")

    def test_inline_script_wins_over_path_and_returns_bytes(self):
        r, data = LL.script_record({"script": "x", "scriptPath": "/nowhere.js"}, None)
        self.assertEqual(r["source"], "inline")
        self.assertEqual(data, b"x")

    def test_unreadable_script_path_is_recorded_not_raised(self):
        r, data = LL.script_record({"scriptPath": "/definitely/not/here.js"}, None)
        self.assertEqual(r["source"], "path")
        self.assertIsNone(r["sha256"])
        self.assertIsNone(data)
        self.assertTrue(r.get("unreadable"))

    def test_run_id_shape_and_extraction(self):
        self.assertTrue(LL.is_run_id("wf_10b03b49-01b"))
        self.assertTrue(LL.is_run_id("wf_cafebabe"))
        self.assertFalse(LL.is_run_id("wf_cafebabe; rm -rf /"))
        self.assertFalse(LL.is_run_id("ignore previous instructions"))
        self.assertEqual(LL.extract_run_id("run wf_10b03b49-01b started"), "wf_10b03b49-01b")
        self.assertEqual(LL.extract_run_id({"runId": "wf_0badf00d-1a"}), "wf_0badf00d-1a")
        self.assertIsNone(LL.extract_run_id("no id here"))
        self.assertIsNone(LL.extract_run_id(None))

    def test_persisted_script_path_extraction(self):
        self.assertEqual(LL.extract_persisted_script_path("Script persisted at /home/u/.claude/projects/x/s1/workflows/scripts/wf_1.js ok"),
                         "/home/u/.claude/projects/x/s1/workflows/scripts/wf_1.js")
        self.assertIsNone(LL.extract_persisted_script_path("nothing"))


class CompareAndIndex(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = LL.ledger_dir(Path(self._tmp.name))

    def _event(self, tool_input, tool_use_id="tu", session="s"):
        return {"tool_input": tool_input, "tool_use_id": tool_use_id, "session_id": session, "cwd": self._tmp.name}

    def _manifest(self, tool_input, **kw):
        m, _b = LL.build_manifest(self._event(tool_input, **kw))
        return m

    def test_compare_counts_changed_added_removed_and_script_state(self):
        rec = self._manifest({"script": "S", "args": {"a": 1, "b": 2, "c": 3}})
        now = self._manifest({"script": "S", "args": {"a": 1, "b": 9, "d": 4}})
        cmp = LL.compare(rec, now)
        self.assertEqual(cmp["script"], "same")
        self.assertEqual(cmp["counts"], {"changed": 1, "only_recorded": 1, "only_now": 1, "order": 0, "total": 3})
        self.assertEqual(cmp["args"], "differ")
        self.assertEqual(sorted(df["key"] for df in cmp["args_diff"]), ["b", "c", "d"])

    def test_compare_script_differs_and_inconclusive(self):
        rec = self._manifest({"script": "S", "args": {}})
        self.assertEqual(LL.compare(rec, self._manifest({"script": "T", "args": {}}))["script"], "differs")
        self.assertEqual(LL.compare(rec, self._manifest({"scriptPath": "/nope.js", "args": {}}))["script"], "inconclusive")
        self.assertEqual(LL.compare(self._manifest({"scriptPath": "/nope.js"}), self._manifest({"scriptPath": "/nope2.js"}))["script"], "inconclusive",
                         "two unavailable hashes are NOT a match")

    def test_compare_absent_vs_present_args(self):
        cmp = LL.compare(self._manifest({"script": "S"}), self._manifest({"script": "S", "args": {}}))
        self.assertEqual(cmp["counts"]["total"], 1)
        self.assertEqual(cmp["args_diff"][0]["key"], "<args>")

    def test_block_reason_is_counts_only(self):
        rec = self._manifest({"script": "S", "args": {"secret-key-name": 1}})
        now = self._manifest({"script": "T", "args": {"secret-key-name": 2}})
        reason = LL.format_block_reason("wf_0badf00d-1a", LL.compare(rec, now), rec["launch_id"])
        self.assertNotIn("secret-key-name", reason)
        self.assertIn("1 key(s) changed", reason)
        self.assertIn("script hash differs", reason)

    def test_write_snapshot_bind_lookup_and_rebind(self):
        m, data = LL.build_manifest(self._event({"script": "S", "args": {"x": 1}}, tool_use_id="tu-1"))
        LL.write_manifest(m, self.d, data)
        self.assertEqual(LL.load_snapshot(self.d, m), b"S")
        self.assertIsNone(LL.find_launch_for_run(self.d, "wf_00000000-00"))
        found = LL.find_launch_by_tool_use(self.d, "tu-1")
        self.assertEqual(found["launch_id"], m["launch_id"])
        LL.bind_run(self.d, found, "wf_00000000-00", "by_tool_use")
        again = LL.find_launch_for_run(self.d, "wf_00000000-00")
        self.assertEqual(again["run_id"], "wf_00000000-00")
        LL.bind_run(self.d, again, "wf_11111111-11", "manual")
        self.assertIsNone(LL.find_launch_for_run(self.d, "wf_00000000-00"))
        self.assertEqual(LL.find_launch_for_run(self.d, "wf_11111111-11")["launch_id"], m["launch_id"])
        kinds = [ln["kind"] for ln in LL.iter_index(self.d)]
        self.assertEqual(kinds, ["launch", "bind", "unbind", "bind"])

    def test_bind_refuses_malformed_run_id(self):
        m, data = LL.build_manifest(self._event({"script": "S"}))
        LL.write_manifest(m, self.d, data)
        with self.assertRaises(ValueError):
            LL.bind_run(self.d, m, "not a run id", "manual")

    def test_decide_pre_records_every_call_and_blocks_only_verified_args_diff(self):
        m, data = LL.build_manifest(self._event({"script": "S", "args": {"x": 1}}, tool_use_id="tu-1"))
        LL.write_manifest(m, self.d, data)
        LL.bind_run(self.d, m, "wf_11111111-11", "by_tool_use")
        d_ok, m_ok = LL.decide_pre(self._event({"script": "S", "args": {"x": 1}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-2"), self.d, env={}, git_budget_s=0.2)
        self.assertEqual(d_ok, {})
        self.assertEqual(m_ok["guard"]["result"], "match")
        d_bad, m_bad = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-3"), self.d, env={}, git_budget_s=0.2)
        self.assertEqual(d_bad.get("decision"), "block")
        self.assertEqual(m_bad["guard"]["result"], "mismatch_blocked")
        d_scr, m_scr = LL.decide_pre(self._event({"script": "T", "args": {"x": 1}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-4"), self.d, env={}, git_budget_s=0.2)
        self.assertNotIn("decision", d_scr)
        self.assertEqual(m_scr["guard"]["result"], "mismatch_script_advisory")
        d_inc, m_inc = LL.decide_pre(self._event({"scriptPath": "/nope.js", "args": {"x": 1}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-5"), self.d, env={"CEO_WORKFLOW_SCRIPT_GUARD": "enforce"}, git_budget_s=0.2)
        self.assertEqual(d_inc, {})
        self.assertEqual(m_inc["guard"]["result"], "inconclusive")
        launches = [ln for ln in LL.iter_index(self.d) if ln["kind"] == "launch"]
        self.assertEqual(len(launches), 5, "every call is recorded, blocked or not")

    def test_unbound_launches_honours_session_and_unbind(self):
        a, da = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-a", session="s-A"))
        b, db = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-b", session="s-B"))
        LL.write_manifest(a, self.d, da)
        LL.write_manifest(b, self.d, db)
        self.assertEqual(LL.unbound_launches(self.d, "s-A"), [a["launch_id"]])
        self.assertEqual(sorted(LL.unbound_launches(self.d, None)), sorted([a["launch_id"], b["launch_id"]]))
        LL.bind_run(self.d, a, "wf_aaaaaaaa-01", "manual")
        self.assertEqual(LL.unbound_launches(self.d, "s-A"), [])

    def test_unbound_launches_excludes_attempts_the_guard_blocked(self):
        m, data = LL.build_manifest(self._event({"script": "S", "args": {"x": 1}}, tool_use_id="tu-1"))
        LL.write_manifest(m, self.d, data)
        LL.bind_run(self.d, m, "wf_11111111-11", "by_tool_use")
        d_bad, m_bad = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-2"), self.d, env={}, git_budget_s=0.2)
        self.assertEqual(d_bad.get("decision"), "block")
        _d_ok, m_ok = LL.decide_pre(self._event({"script": "S", "args": {"x": 1}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-3"), self.d, env={}, git_budget_s=0.2)
        self.assertEqual(LL.unbound_launches(self.d, "s"), [m_ok["launch_id"]], "a blocked attempt never ran: not a candidate")
        lines = {ln["launch_id"]: ln for ln in LL.iter_index(self.d) if ln["kind"] == "launch"}
        self.assertTrue(lines[m_bad["launch_id"]]["blocked"])
        self.assertEqual(lines[m_bad["launch_id"]]["guard"], "mismatch_blocked")
        self.assertFalse(lines[m_ok["launch_id"]]["blocked"])
        self.assertEqual(lines[m["launch_id"]]["guard"], "none")

    def _bound(self, tool_input, run="wf_11111111-11", method="by_tool_use"):
        m, data = LL.build_manifest(self._event(tool_input, tool_use_id="tu-rec"))
        LL.write_manifest(m, self.d, data)
        return LL.bind_run(self.d, m, run, method)

    def test_force_declaration_grammar(self):
        ok = {"CEO_WORKFLOW_RESUME_FORCE: why": "why", "CEO_WORKFLOW_RESUME_FORCE:why": "why",
              "CEO_WORKFLOW_RESUME_FORCE:  spaced  ": "spaced", "CEO_WORKFLOW_RESUME_FORCE: \ud800": "\ud800"}
        for text, reason in ok.items():
            self.assertEqual(LL.force_declaration(text), reason, repr(text))
        self.assertEqual(len(LL.force_declaration("CEO_WORKFLOW_RESUME_FORCE: " + "r" * 5000)), LL.FORCE_REASON_MAX)
        for bad in ["CEO_WORKFLOW_RESUME_FORCE:", "CEO_WORKFLOW_RESUME_FORCE:   \n\t", " CEO_WORKFLOW_RESUME_FORCE: x",
                    "x CEO_WORKFLOW_RESUME_FORCE: y", "ceo_workflow_resume_force: x", "CEO_WORKFLOW_RESUME_FORCE x",
                    "", None, 7, 1.5, True, ["CEO_WORKFLOW_RESUME_FORCE: x"], {"CEO_WORKFLOW_RESUME_FORCE:": "x"}]:
            self.assertIsNone(LL.force_declaration(bad), repr(bad))

    def test_manifest_problem_names_every_inconsistency(self):
        good = self._bound({"script": "S", "args": {"x": 1}})
        self.assertIsNone(LL.manifest_problem(good, self.d))
        snap = LL.snapshot_path(self.d, good["launch_id"])

        def variant(fn):
            m = json.loads(json.dumps(good))
            fn(m)
            return LL.manifest_problem(m, self.d)

        self.assertEqual(LL.manifest_problem([], self.d), "not_an_object")
        self.assertEqual(variant(lambda m: m.update(schema="other")), "schema")
        self.assertEqual(variant(lambda m: m.update(launch_id="../../x")), "launch_id")
        self.assertEqual(variant(lambda m: m.update(run_id="nope")), "run_id")
        self.assertEqual(variant(lambda m: m.update(bind_method="guess")), "bind_method")
        self.assertEqual(variant(lambda m: m["args"].pop("canonical")), "args_shape")
        self.assertEqual(variant(lambda m: m["args"].update(sha256="zz")), "args_shape")
        self.assertEqual(variant(lambda m: m["args"].update(present="yes")), "args_shape")
        self.assertEqual(variant(lambda m: m["args"].update(canonical='{"x":2}')), "args_inconsistent")
        self.assertEqual(variant(lambda m: m["args"].update(present=False)), "args_inconsistent")
        self.assertEqual(variant(lambda m: m.update(script="S")), "script_shape")
        self.assertEqual(variant(lambda m: m["script"].update(sha256="ab")), "script_shape")
        self.assertEqual(variant(lambda m: m.update(script_snapshot=None)), "script_snapshot_missing")
        absent = self._bound({"script": "S"}, run="wf_22222222-22")
        self.assertIsNone(LL.manifest_problem(absent, self.d), "absent args (canonical ABSENT, present False) is consistent")
        snap.write_bytes(b"T")
        self.assertEqual(LL.manifest_problem(good, self.d), "script_snapshot_mismatch")
        snap.unlink()
        self.assertEqual(LL.manifest_problem(good, self.d), "script_snapshot_missing")
        named, _b = LL.build_manifest(self._event({"name": "saved-flow"}, tool_use_id="tu-named"))
        LL.write_manifest(named, self.d, None)
        named = LL.bind_run(self.d, named, "wf_33333333-33", "manual")
        self.assertIsNone(LL.manifest_problem(named, self.d), "no script hash ⇒ nothing to check against a snapshot")

    def test_guard_exception_is_recorded_inconclusive_and_the_call_still_recorded(self):
        self._bound({"script": "S", "args": {"x": 1}})
        original = LL.compare

        def boom(*_a, **_k):
            raise RuntimeError("synthetic")

        LL.compare = boom
        try:
            dec, m = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-x"), self.d, env={}, git_budget_s=0.2)
        finally:
            LL.compare = original
        self.assertEqual(dec, {})
        self.assertEqual((m["guard"]["result"], m["guard"]["error"]), ("inconclusive", "RuntimeError"))
        on_disk = LL.load_manifest(self.d, m["launch_id"])
        self.assertIsNotNone(on_disk, "the call is recorded even when the guard raised")
        self.assertEqual(on_disk["guard"]["result"], "inconclusive")

    def test_a_computed_block_survives_a_failure_to_persist_the_call(self):
        self._bound({"script": "S", "args": {"x": 1}})
        original = LL.write_manifest

        def refuse(*_a, **_k):
            raise OSError("disk full")

        LL.write_manifest = refuse
        try:
            dec, m = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-y"), self.d, env={}, git_budget_s=0.2)
        finally:
            LL.write_manifest = original
        self.assertEqual(dec.get("decision"), "block")
        self.assertEqual(m["write_error"], "OSError")

    def test_index_and_manifest_reads_skip_garbage_never_raise(self):
        idx = self.d / LL.INDEX_NAME
        good_unbound = "L-20260917T120000-deadbeef"
        lines = ["not json", "[1, 2]", '{"no_kind": 1}', '{"kind": 5}', "[" * 200000,
                 '{"kind": "launch", "session_id": "s"}',
                 '{"kind": "launch", "launch_id": "../../etc/passwd", "session_id": "s"}',
                 '{"kind": "launch", "launch_id": "%s", "session_id": "s", "blocked": "false"}' % good_unbound,
                 '{"kind": "launch", "launch_id": "L-20260917T120001-cafebabe", "session_id": "s", "blocked": true}']
        idx.write_text("\n".join(lines) + "\n\udcff\n".encode("utf-8", "surrogateescape").decode("utf-8", "replace"), encoding="utf-8")
        with open(idx, "ab") as fh:
            fh.write(b"\xff\xfe not utf-8\n")
        kinds = [ln["kind"] for ln in LL.iter_index(self.d)]
        self.assertEqual(kinds, ["launch", "launch", "launch", "launch"])
        self.assertEqual(LL.unbound_launches(self.d, "s"), [good_unbound], "only a well-shaped, non-blocked launch is a candidate")
        self.assertIsNone(LL.load_manifest(self.d, "../../etc/passwd"))
        (self.d.parent / "escape.json").write_text('{"schema": "planted outside the ledger"}', encoding="utf-8")
        self.assertIsNone(LL.load_manifest(self.d, "../escape"), "an id that is not launch-shaped never resolves to a file, even an existing one")
        self.assertIsNone(LL.load_manifest(self.d, 42))
        (self.d / ("%s.json" % good_unbound)).write_text("[" * 200000, encoding="utf-8")
        self.assertIsNone(LL.load_manifest(self.d, good_unbound), "a too-deep document is unreadable, not an exception")
        out = LL.decide_post({"tool_response": "run wf_deadbeef-01 ok", "session_id": "s"}, self.d)
        self.assertIsNone(out, "the only candidate's manifest is unreadable: orphan, never a crash")

    def test_lookup_walks_back_when_the_latest_binding_is_rebound_away(self):
        a = self._bound({"script": "S", "args": {"x": 1}}, run="wf_11111111-11")
        b, data = LL.build_manifest(self._event({"script": "S", "args": {"x": 1}}, tool_use_id="tu-b"))
        LL.write_manifest(b, self.d, data)
        b = LL.bind_run(self.d, b, "wf_11111111-11", "by_tool_use")
        self.assertEqual(LL.find_launch_for_run(self.d, "wf_11111111-11")["launch_id"], b["launch_id"])
        LL.bind_run(self.d, b, "wf_22222222-22", "manual")
        self.assertEqual(LL.find_launch_for_run(self.d, "wf_11111111-11")["launch_id"], a["launch_id"],
                         "the earlier binding that still carries the run is found again")
        self.assertEqual(LL.find_launch_for_run(self.d, "wf_22222222-22")["launch_id"], b["launch_id"])

    def test_unreadable_latest_record_is_never_replaced_by_an_older_launch(self):
        self._bound({"script": "S", "args": {"x": 1}}, run="wf_11111111-11")
        b, data = LL.build_manifest(self._event({"script": "S", "args": {"x": 2}}, tool_use_id="tu-b"))
        LL.write_manifest(b, self.d, data)
        b = LL.bind_run(self.d, b, "wf_11111111-11", "by_tool_use")
        LL.manifest_path(self.d, b["launch_id"]).write_text("{torn", encoding="utf-8")
        self.assertIsNone(LL.find_launch_for_run(self.d, "wf_11111111-11"),
                          "the latest binding's record is unreadable: no evidence, not the older launch's inputs")

    def test_key_order_is_one_difference_and_the_literal_keeps_the_original_order(self):
        rec = self._manifest({"script": "S", "args": {"zeta": 1, "alpha": "first"}})
        now = self._manifest({"script": "S", "args": {"alpha": "first", "zeta": 1}})
        self.assertEqual(rec["args"]["literal"], '{"zeta":1,"alpha":"first"}')
        self.assertEqual(rec["args"]["canonical"], now["args"]["canonical"])
        cmp = LL.compare(rec, now)
        self.assertEqual((cmp["args"], cmp["counts"]["order"], cmp["counts"]["total"]), ("differ", 1, 1))
        self.assertIn("key order differs", LL.format_block_reason("wf_0badf00d-1a", cmp, rec["launch_id"]))

    def test_uncanonicalisable_args_are_recorded_and_the_guard_is_inconclusive(self):
        original = LL.canonical_json

        def deep(_value):
            raise RecursionError("synthetic")

        LL.canonical_json = deep
        try:
            rec = LL.args_record({"args": {"x": 2}})
        finally:
            LL.canonical_json = original
        self.assertEqual((rec["canonical"], rec["literal"], rec["error"]), (None, None, "RecursionError"), "args_record is total")
        self._bound({"script": "S", "args": {"x": 1}})
        original_record = LL.args_record
        LL.args_record = lambda _ti: dict(rec)
        try:
            dec, m = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-deep"),
                                   self.d, env={}, git_budget_s=0.2)
        finally:
            LL.args_record = original_record
        self.assertEqual(dec, {}, "an unverifiable comparison never blocks")
        self.assertEqual((m["guard"]["result"], m["guard"]["integrity"]), ("inconclusive", "args_uncanonicalized"))
        self.assertIsNotNone(LL.load_manifest(self.d, m["launch_id"]), "the call is recorded")

    def test_construction_failure_is_recorded_inconclusive(self):
        original = LL.build_manifest

        def boom(*_a, **_k):
            raise MemoryError("synthetic")

        LL.build_manifest = boom
        try:
            dec, m = LL.decide_pre(self._event({"script": "S", "args": {"x": 2}, "resumeFromRunId": "wf_11111111-11"}, tool_use_id="tu-b"),
                                   self.d, env={}, git_budget_s=0.2)
        finally:
            LL.build_manifest = original
        self.assertEqual(dec, {})
        self.assertEqual(m["guard"], {"result": "inconclusive", "error": "build:MemoryError", "diff": [], "counts": {}})
        on_disk = LL.load_manifest(self.d, m["launch_id"])
        self.assertEqual(on_disk["tool_use_id"], "tu-b")
        self.assertEqual(LL.manifest_problem(dict(on_disk, run_id="wf_11111111-11", bind_method="manual"), self.d), "args_uncanonicalized")

    def test_script_fields_must_agree_with_their_source(self):
        good = self._bound({"script": "S", "args": {"x": 1}})
        self.assertIsNone(LL.manifest_problem(good, self.d))

        def variant(fn):
            m = json.loads(json.dumps(good))
            fn(m)
            return LL.manifest_problem(m, self.d)

        self.assertEqual(variant(lambda m: m["script"].pop("sha256")), "script_shape", "a missing hash is not an unavailable one")
        self.assertEqual(variant(lambda m: m["script"].update(sha256=None)), "script_shape", "an inline script always has a hash")
        self.assertEqual(variant(lambda m: m["script"].update(source="named")), "script_shape")
        self.assertEqual(variant(lambda m: m["script"].update(source="mystery")), "script_shape")
        self.assertEqual(variant(lambda m: m["args"].update(literal='{"x":2}')), "args_inconsistent")
        self.assertEqual(variant(lambda m: m["args"].pop("literal")), "args_shape")
        self.assertEqual(variant(lambda m: m["args"].update(canonical='{"x":2}', literal='{"x":2}')), "args_inconsistent",
                         "texts rewritten consistently but the recorded hashes are the old ones")
        unreadable, _b = LL.build_manifest(self._event({"scriptPath": "/nope/missing.js", "args": {"x": 1}}, tool_use_id="tu-u"))
        LL.write_manifest(unreadable, self.d, None)
        unreadable = LL.bind_run(self.d, unreadable, "wf_44444444-44", "manual")
        self.assertIsNone(LL.manifest_problem(unreadable, self.d))
        forged = json.loads(json.dumps(unreadable))
        forged["script"]["sha256"] = "a" * 64
        self.assertEqual(LL.manifest_problem(forged, self.d), "script_shape", "an unreadable script cannot carry a hash")

    def test_run_id_extraction_uses_the_label_and_never_guesses(self):
        real = ("Workflow launched in background. Task ID: wclla6jmn\n"
                "Transcript dir: /h/.claude/projects/x/s/subagents/workflows/wf_a773a8fa-6f7\n"
                "Script file: /tmp/probe.script\nRun ID: wf_a773a8fa-6f7\n"
                "To resume after editing the script: Workflow({scriptPath: \"/tmp/probe.script\", resumeFromRunId: \"wf_a773a8fa-6f7\"})")
        self.assertEqual(LL.extract_run_id(real), "wf_a773a8fa-6f7")
        self.assertEqual(LL.extract_run_id("output quoting wf_11111111-01 first\nRun ID: wf_22222222-02"), "wf_22222222-02")
        self.assertIsNone(LL.extract_run_id("Run ID: wf_11111111-01\nRun ID: wf_22222222-02"), "two labelled ids: ambiguous")
        self.assertIsNone(LL.extract_run_id("resumed wf_11111111-01 into wf_22222222-02"), "two unlabelled ids: ambiguous")
        self.assertEqual(LL.extract_run_id("started wf_33333333-03, see wf_33333333-03"), "wf_33333333-03")
        self.assertEqual(LL.extract_run_id({"runId": "wf_44444444-04", "text": "wf_55555555-05"}), "wf_44444444-04")

    def test_a_second_record_of_a_bound_tool_use_is_never_a_candidate(self):
        first, d1 = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-dup", session="s"))
        LL.write_manifest(first, self.d, d1)
        second, d2 = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-dup", session="s"), now=1.0e9)
        LL.write_manifest(second, self.d, d2)
        bound = LL.decide_post({"tool_response": "Run ID: wf_66666666-06", "session_id": "s", "tool_use_id": "tu-dup"}, self.d)
        self.assertIsNotNone(bound)
        self.assertEqual(LL.unbound_launches(self.d, "s"), [], "the other record of the same call is not pending work")

    def test_decide_post_orphans_instead_of_guessing(self):
        a, da = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-a", session="s"))
        b, db = LL.build_manifest(self._event({"script": "S"}, tool_use_id="tu-b", session="s"))
        LL.write_manifest(a, self.d, da)
        LL.write_manifest(b, self.d, db)
        out = LL.decide_post({"tool_response": "run wf_deadbeef-01 ok", "session_id": "s"}, self.d)
        self.assertIsNone(out)
        self.assertEqual([ln["kind"] for ln in LL.iter_index(self.d)][-1], "orphan")
        out2 = LL.decide_post({"tool_response": "run wf_deadbeef-02 ok", "session_id": "s", "tool_use_id": "tu-b"}, self.d)
        self.assertEqual(out2["run_id"], "wf_deadbeef-02")
        self.assertEqual(out2["bind_method"], "by_tool_use")
