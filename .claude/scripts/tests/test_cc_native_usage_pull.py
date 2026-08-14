"""Tests for cc-native-usage-pull.py (PLAN-178 W1.2-1).

Stdlib-only. The puller is imported via importlib (dash in filename). ALL
filesystem fixtures live under TestEnvContext's isolated HOME — the real
``~/.claude`` is NEVER touched (TestEnvContext repoints HOME +
CLAUDE_PROJECT_DIR at a per-test tmp tree, so ``native_root()`` resolves
INSIDE the sandbox; asserted in setUp). Covers:

  - dormant fail-soft: root absent, and sessions without ``subagents/`` ->
    exit 0 + {"available": false, "dormant": true} as valid JSON on stdout
  - synthetic task+workflow corpus: rail from PATH SHAPE, meta model wins on
    the task path, transcript message.model fallback on the workflow path,
    token sums from message.usage, truncated live-tail line tolerated
  - journal.jsonl NEVER enters the rollup (counted in skipped.journal_excluded)
  - unreadable meta -> agent skipped + counted (skipped.meta_unreadable),
    stderr breadcrumb, stdout stays pure JSON
  - orphan .jsonl with no paired meta -> kept as agentType "unknown-no-meta",
    rail still inferred from the path (probe S1.2 edge)
  - no-network doctrine: the module source imports no urllib/socket/requests
"""
from __future__ import annotations

import contextlib
import io
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_SCRIPT_PATH = _THIS_DIR.parent / "cc-native-usage-pull.py"
_REPO_ROOT = _THIS_DIR.parent.parent.parent

_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("cc_native_usage_pull", _SCRIPT_PATH)
nup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nup)  # type: ignore[union-attr]


def _usage_line(inp=0, out=0, cache_creation=0, cache_read=0, model=None):
    msg = {"usage": {"input_tokens": inp, "output_tokens": out,
                     "cache_creation_input_tokens": cache_creation,
                     "cache_read_input_tokens": cache_read}}
    if model:
        msg["model"] = model
    return json.dumps({"type": "assistant", "message": msg})


def _run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = nup.main(argv)
    return rc, out.getvalue(), err.getvalue()


class _NativeCorpusBase(TestEnvContext):
    """Fixture base: builds the native tree at the EXACT root the puller derives."""

    SESSION = "0f0e0d0c-aaaa-bbbb-cccc-000011112222"

    def setUp(self):
        super().setUp()
        # Env-hygiene contract (mock.patch.dict, codex S306 r4 P2 cure): a
        # CEO_NATIVE_COST_DISABLE=1 leaking from the parent environment would
        # turn every _run_main into the disabled payload and mask the
        # fixtures. Snapshot + pop; the patcher restores on teardown.
        env_patch = mock.patch.dict(os.environ)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        os.environ.pop("CEO_NATIVE_COST_DISABLE", None)
        # TestEnvContext already repointed HOME + CLAUDE_PROJECT_DIR at the
        # isolated tmp tree — native_root() must resolve INSIDE it.
        self.root = Path(nup.native_root())
        self.assertTrue(str(self.root).startswith(str(self.home_dir)),
                        "fixture root escaped the isolated HOME: %s" % self.root)

    def _subagents(self, session=None):
        sub = self.root / (session or self.SESSION) / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        return sub

    @staticmethod
    def _write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class TestDormantFailSoft(_NativeCorpusBase):
    def test_missing_root_is_dormant_exit_0(self):
        self.assertFalse(self.root.exists())
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertFalse(payload["available"])
        self.assertTrue(payload["dormant"])
        self.assertIn("absent", payload["reason"])

    def test_sessions_without_subagents_is_dormant(self):
        (self.root / self.SESSION).mkdir(parents=True)   # session dir, NO subagents/
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertFalse(payload["available"])
        self.assertTrue(payload["dormant"])
        self.assertIn("subagents", payload["reason"])


class TestCorpusRollup(_NativeCorpusBase):
    def test_task_and_workflow_rails_from_path_shape(self):
        sub = self._subagents()
        # task rail — teammate-shaped meta (probe S1.4 exemplar A); meta model WINS
        # over the transcript's message.model ("opus" alias below).
        self._write(sub / "agent-aresearcher-0123456789abcdef.meta.json",
                    json.dumps({"agentType": "researcher", "name": "researcher",
                                "spawnDepth": 0, "model": "claude-opus-5",
                                "taskKind": "in_process_teammate"}))
        self._write(sub / "agent-aresearcher-0123456789abcdef.jsonl", "\n".join([
            _usage_line(100, 10, cache_creation=5, cache_read=50, model="opus"),
            json.dumps({"type": "user", "message": {"role": "user"}}),  # no usage
            _usage_line(200, 20, cache_read=25),
            '{"type": "assistant", "message": {"usage": {"input_tokens": 1',  # live tail
        ]) + "\n")
        # workflow rail — minimal meta (exemplar C): model comes from the TRANSCRIPT
        wf = sub / "workflows" / "wf_deadbeef-cafe"
        self._write(wf / "agent-a0123456789abcdef0.meta.json",
                    json.dumps({"agentType": "workflow-subagent", "spawnDepth": 1}))
        self._write(wf / "agent-a0123456789abcdef0.jsonl",
                    _usage_line(1000, 100, cache_creation=7, cache_read=3,
                                model="claude-fable-5") + "\n")
        # journal — same wf dir, HUGE numbers that must never reach the rollup
        self._write(wf / "journal.jsonl", _usage_line(999999, 999999) + "\n")

        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["sessions_with_subagents"], 1)
        agents = {a["agent"]: a for a in payload["agents"]}
        self.assertEqual(len(agents), 2)

        task = agents["agent-aresearcher-0123456789abcdef"]
        self.assertEqual(task["rail"], "task")
        self.assertEqual(task["session_id"], self.SESSION)
        self.assertEqual(task["agentType"], "researcher")
        self.assertEqual(task["model"], "claude-opus-5")   # meta wins over message.model
        self.assertEqual(task["tokens"], {"input": 300, "output": 30,
                                          "cache_creation": 5, "cache_read": 75})
        self.assertEqual(task["usage_events"], 2)

        wf_rec = agents["agent-a0123456789abcdef0"]
        self.assertEqual(wf_rec["rail"], "workflow")
        self.assertEqual(wf_rec["agentType"], "workflow-subagent")
        self.assertEqual(wf_rec["model"], "claude-fable-5")  # transcript fallback
        self.assertEqual(wf_rec["workflow_id"], "wf_deadbeef-cafe")
        self.assertEqual(wf_rec["tokens"]["input"], 1000)

        totals = payload["totals"]
        self.assertEqual(totals["task"]["tokens"]["input"], 300)
        self.assertEqual(totals["workflow"]["tokens"]["input"], 1000)
        self.assertEqual(totals["all"]["tokens"]["input"], 1300)  # journal NOT here
        self.assertEqual(totals["all"]["tokens"]["output"], 130)
        self.assertEqual(totals["all"]["agents"], 2)
        self.assertEqual(totals["all"]["usage_events"], 3)
        self.assertEqual(payload["skipped"]["journal_excluded"], 1)
        self.assertEqual(payload["skipped"]["malformed_lines"], 1)  # truncated tail

    def test_journal_only_workflow_yields_no_agents(self):
        sub = self._subagents()
        self._write(sub / "workflows" / "wf_0001" / "journal.jsonl",
                    _usage_line(12345, 678) + "\n")
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["agents"], [])
        self.assertEqual(payload["skipped"]["journal_excluded"], 1)
        self.assertEqual(payload["totals"]["all"]["tokens"]["input"], 0)

    def test_root_override_and_compact_output(self):
        alt = Path(tempfile.mkdtemp()) / "projects-root"
        sub = alt / self.SESSION / "subagents"
        sub.mkdir(parents=True)
        self._write(sub / "agent-a1111111111111111.meta.json",
                    json.dumps({"agentType": "general-purpose", "spawnDepth": 1}))
        self._write(sub / "agent-a1111111111111111.jsonl", _usage_line(42, 7) + "\n")
        rc, out, _err = _run_main(["--root", str(alt), "--compact"])
        self.assertEqual(rc, 0)
        self.assertNotIn("\n", out.strip())              # --compact = single line
        payload = json.loads(out)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["totals"]["all"]["tokens"]["input"], 42)


class TestMetaEdges(_NativeCorpusBase):
    def test_unreadable_meta_skips_agent_with_count(self):
        sub = self._subagents()
        self._write(sub / "agent-abad0123456789abcd.meta.json", "{this is not json")
        self._write(sub / "agent-abad0123456789abcd.jsonl", _usage_line(50, 5) + "\n")
        rc, out, err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)                        # stdout stays pure JSON
        self.assertEqual(payload["agents"], [])
        self.assertEqual(payload["skipped"]["meta_unreadable"], 1)
        self.assertEqual(payload["totals"]["all"]["agents"], 0)
        self.assertEqual(payload["totals"]["all"]["tokens"]["input"], 0)
        self.assertIn("unreadable meta", err)            # breadcrumb on stderr

    def test_orphan_jsonl_without_meta_is_kept_as_unknown(self):
        # probe S1.2: 1 task-rail transcript in today's corpus has no meta.
        sub = self._subagents()
        self._write(sub / "agent-a0rphan12345678901.jsonl", _usage_line(10, 1) + "\n")
        self._write(sub / "workflows" / "wf_00000001" / "agent-a0rphan99999999999.jsonl",
                    _usage_line(20, 2) + "\n")
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        agents = sorted(payload["agents"], key=lambda a: a["rail"])
        self.assertEqual([a["rail"] for a in agents], ["task", "workflow"])
        for rec in agents:
            self.assertEqual(rec["agentType"], "unknown-no-meta")
        self.assertEqual(agents[1]["workflow_id"], "wf_00000001")
        self.assertEqual(payload["totals"]["all"]["tokens"]["input"], 30)


class TestDriftSondas(_NativeCorpusBase):
    """Fingerprint drift sondas (probe §2 / codex S306 P1 cure): schema drift
    degrades to available:false — never misleading totals. Positive controls:
    each test FAILS if the drift gate is removed."""

    def test_usage_without_core_keys_degrades_to_unavailable(self):
        sub = self._subagents()
        self._write(sub / "agent-adrift123456789012.meta.json",
                    json.dumps({"agentType": "general-purpose", "spawnDepth": 1}))
        drifted = json.dumps({"message": {"usage": {"weird_new_field": 7}}})
        self._write(sub / "agent-adrift123456789012.jsonl", drifted + "\n")
        rc, out, err = _run_main([])
        self.assertEqual(rc, 0)                          # fail-soft by contract
        payload = json.loads(out)
        self.assertFalse(payload["available"])           # sonda fired -> fallback
        self.assertEqual(payload["drift"]["usage_missing_core_keys"], 1)
        # nothing silenced: the record is still present, with ZERO events
        self.assertEqual(payload["agents"][0]["usage_events"], 0)
        self.assertIn("schema drift", err)               # breadcrumb on stderr

    def test_meta_without_invariants_degrades_to_unavailable(self):
        sub = self._subagents()
        self._write(sub / "agent-anoinv12345678901a.meta.json",
                    json.dumps({"description": "meta lost its invariants"}))
        self._write(sub / "agent-anoinv12345678901a.jsonl", _usage_line(10, 1) + "\n")
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["drift"]["meta_invariant_missing"], 1)

    def test_clean_corpus_reports_zero_drift_and_available(self):
        sub = self._subagents()
        self._write(sub / "agent-aclean1234567890ab.meta.json",
                    json.dumps({"agentType": "general-purpose", "spawnDepth": 1}))
        self._write(sub / "agent-aclean1234567890ab.jsonl", _usage_line(10, 1) + "\n")
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["drift"],
                         {"usage_missing_core_keys": 0,
                          "meta_invariant_missing": 0,
                          "path_shape_zero_glob": 0})

    def test_zero_glob_with_subagents_is_path_shape_drift(self):
        # codex S306 r2 P2 cure: subagents/ exists (an agent HAS spawned) but
        # both known globs match nothing => the harness moved the layout.
        sub = self._subagents()
        moved = sub / "v2-new-level" / "agent-amoved12345678901.jsonl"
        self._write(moved, _usage_line(10, 1) + "\n")
        rc, out, _err = _run_main([])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["drift"]["path_shape_zero_glob"], 1)


class TestNoNetworkDoctrine(TestEnvContext):
    def test_module_source_has_no_network_imports(self):
        src = Path(_SCRIPT_PATH).read_text(encoding="utf-8")
        for banned in ("import urllib", "import socket", "import requests",
                       "import http", "from urllib", "from socket", "from http"):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
