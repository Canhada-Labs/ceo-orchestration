"""Behaviour battery for ``await_release_gate.decide`` (PLAN-166 W0 item 6, F1).

The AC-2 enumeration in PLAN-166 is the ONLY source for what is covered here.
No test count is asserted or written anywhere — a mirrored numeral has drifted
from reality four times in this plan; the enumeration below IS the census.

Case classes, in AC-2 order:

* GRANT — exact candidate (release.yml + push + tag + sha + fresh) whose
  ``release-gate`` job concluded ``success``. MANDATORY: without it an
  always-BLOCK implementation would pass the entire battery.
* NEVER-GRANT — payloads holding ONLY green NON-candidate runs (rc tag,
  other sha, wrong workflow, workflow_dispatch). Each proves twice over that
  a look-alike green run neither grants NOR falsely blocks the race.
* BLOCK — candidate gate ``skipped``; candidate gate ``failure``; no
  candidate with the deadline elapsed; malformed JSON.
* WAIT — empty run list in time; candidate present with the ``release-gate``
  job absent from the jobs payload in time (eventual consistency); candidate
  with ``conclusion: null`` in time (this one kills the naive
  ``!= "failure"`` implementation).
* FRESHNESS — a ``success`` candidate created BEFORE the asking run started
  (delete + re-tag of the same sha) does not count as GRANT.
* USAGE — the freshness input is load-bearing, so it has no default:
  omitting ``--self-created-at`` (or passing an empty value) is a usage
  error (exit 2), NEVER a run with the delete+re-tag leg silently off.
  Without this class the FRESHNESS tests above prove nothing about the W1
  wiring — the same stale payload they reject becomes a GRANT the moment
  the caller forgets one flag.
"""

from __future__ import annotations

import calendar
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Env-hygiene gate (check-test-env-hygiene.py): test classes subclass
# TestEnvContext, not bare unittest.TestCase, so HOME / CLAUDE_PROJECT_DIR /
# os.environ / sys.path are snapshot-restored around every test.
_HOOKS_DIR = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

from await_release_gate import (
    BLOCK,
    EXIT_BLOCK,
    EXIT_GRANT,
    EXIT_USAGE,
    EXIT_WAIT,
    GRANT,
    WAIT,
    GateContext,
    decide,
)

SCRIPT = Path(__file__).resolve().parent.parent / "await_release_gate.py"

TAG = "v1.3.0"
HEAD_SHA = "a" * 40
OTHER_SHA = "b" * 40

# Independent clock: built with calendar.timegm, NOT with the module's own
# parser, so the fixtures are not graded by the code under test.
SELF_CREATED_AT = "2026-08-05T12:00:00Z"
SELF_EPOCH = calendar.timegm((2026, 8, 5, 12, 0, 0, 0, 1, -1))
CANDIDATE_CREATED_AT = "2026-08-05T12:00:05Z"       # same push, +5s jitter
STALE_CREATED_AT = "2026-08-05T11:00:00Z"           # previous tag push, -1h
NOW = SELF_EPOCH + 60
DEADLINE_OPEN = SELF_EPOCH + 1800                   # 30 min of head-room
NOW_PAST_DEADLINE = DEADLINE_OPEN + 1


def ctx(now=NOW, deadline=DEADLINE_OPEN):
    """Context with EVERY input pinned explicitly (no ambient clock)."""
    return GateContext(
        tag=TAG,
        head_sha=HEAD_SHA,
        now_epoch=now,
        deadline_epoch=deadline,
        self_created_at_epoch=SELF_EPOCH,
        freshness_skew_seconds=120,
    )


def gate_job(conclusion="success", status="completed"):
    return {"name": "release-gate", "status": status, "conclusion": conclusion}


def release_run(**over):
    """A run that matches the candidate identity on every field by default."""
    run = {
        "id": 1001,
        "run_attempt": 1,
        "path": ".github/workflows/release.yml",
        "event": "push",
        "head_branch": TAG,
        "head_sha": HEAD_SHA,
        "created_at": CANDIDATE_CREATED_AT,
        "status": "completed",
        "conclusion": "success",
        "jobs": [gate_job()],
    }
    run.update(over)
    return run


def self_run():
    """The npm-publish run doing the asking — always in its own head_sha list."""
    return {
        "id": 1002,
        "run_attempt": 1,
        "path": ".github/workflows/npm-publish.yml",
        "event": "push",
        "head_branch": TAG,
        "head_sha": HEAD_SHA,
        "created_at": SELF_CREATED_AT,
        "status": "in_progress",
        "conclusion": None,
        "jobs": [{"name": "await-release-gate", "status": "in_progress", "conclusion": None}],
    }


def payload(*runs):
    return {"workflow_runs": list(runs)}


def run_cli(raw_body, extra=(), self_created_at=SELF_CREATED_AT):
    """CLI harness. ``self_created_at=None`` OMITS the flag entirely."""
    handle, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        fh.write(raw_body)
    freshness = [] if self_created_at is None else ["--self-created-at", self_created_at]
    try:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--payload-file", path,
                "--tag", TAG,
                "--head-sha", HEAD_SHA,
                "--deadline-epoch", str(DEADLINE_OPEN),
                "--now-epoch", str(NOW),
            ] + freshness + list(extra),
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(path)


class GrantTests(TestEnvContext):
    """The mandatory positive control."""

    def test_exact_candidate_with_successful_gate_job_grants(self):
        # The list deliberately also holds the asking npm-publish run: the
        # sibling must be ignored, not raced against.
        result = decide(payload(self_run(), release_run()), ctx())
        self.assertEqual(GRANT, result.decision)
        self.assertEqual("gate-job-success", result.reason)
        self.assertEqual(1, result.facts["fresh_candidates"])

    def test_grant_exits_zero_and_prints_its_inputs(self):
        proc = run_cli(json.dumps(payload(self_run(), release_run())))
        self.assertEqual(EXIT_GRANT, proc.returncode, proc.stderr)
        self.assertIn("decision=GRANT", proc.stdout)
        self.assertIn("freshness_skew_s=120", proc.stdout)
        self.assertIn("head_sha=" + HEAD_SHA, proc.stdout)


class NeverGrantTests(TestEnvContext):
    """Green look-alikes: never GRANT, and never a false BLOCK in time."""

    def _assert_never_grants(self, run):
        body = payload(self_run(), run)
        in_time = decide(body, ctx())
        self.assertEqual(WAIT, in_time.decision)
        self.assertEqual("candidate-not-yet-created", in_time.reason)
        self.assertEqual(0, in_time.facts["identity_matches"])
        expired = decide(body, ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, expired.decision)

    def test_release_gate_success_on_a_different_tag_does_not_grant(self):
        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))

    def test_release_gate_success_on_another_commit_does_not_grant(self):
        self._assert_never_grants(release_run(head_sha=OTHER_SHA, id=2002))

    def test_release_gate_success_from_the_wrong_workflow_does_not_grant(self):
        self._assert_never_grants(
            release_run(path=".github/workflows/validate.yml", id=2003)
        )

    def test_release_gate_success_from_workflow_dispatch_does_not_grant(self):
        self._assert_never_grants(release_run(event="workflow_dispatch", id=2004))


class BlockTests(TestEnvContext):
    def test_candidate_with_skipped_gate_job_blocks(self):
        # CEO_SOTA_DISABLE=1 skips the job while the RUN stays green.
        run = release_run(jobs=[gate_job(conclusion="skipped")])
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-skipped", result.reason)

    def test_candidate_with_failed_gate_job_blocks(self):
        run = release_run(conclusion="failure", jobs=[gate_job(conclusion="failure")])
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-failure", result.reason)
        proc = run_cli(json.dumps(payload(self_run(), run)))
        self.assertEqual(EXIT_BLOCK, proc.returncode)
        self.assertIn("decision=BLOCK", proc.stdout)

    def test_no_candidate_past_the_deadline_blocks(self):
        result = decide(payload(self_run()), ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("deadline-exceeded:candidate-not-yet-created", result.reason)

    def test_malformed_payloads_block(self):
        for body in ([], "workflow_runs", {"message": "Bad credentials"},
                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
            result = decide(body, ctx())
            self.assertEqual(BLOCK, result.decision, body)
            self.assertEqual("malformed-payload", result.reason, body)
        proc = run_cli("{not json at all")
        self.assertEqual(EXIT_BLOCK, proc.returncode)
        self.assertIn("reason=malformed-payload", proc.stdout)


class WaitTests(TestEnvContext):
    def test_empty_run_list_in_time_waits(self):
        result = decide(payload(), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("candidate-not-yet-created", result.reason)
        proc = run_cli(json.dumps(payload()))
        self.assertEqual(EXIT_WAIT, proc.returncode)

    def test_candidate_without_the_gate_job_yet_waits(self):
        # Eventual consistency of the jobs endpoint: absent list AND empty list.
        other_job = {"name": "publish-release", "status": "queued", "conclusion": None}
        for run in (release_run(jobs=[]), release_run(jobs=[other_job])):
            body = payload(self_run(), run)
            result = decide(body, ctx())
            self.assertEqual(WAIT, result.decision)
            self.assertEqual("gate-job-not-materialised", result.reason)
        no_jobs_key = release_run()
        del no_jobs_key["jobs"]
        result = decide(payload(self_run(), no_jobs_key), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("gate-job-not-materialised", result.reason)

    def test_running_gate_job_waits(self):
        # Kills `conclusion != "failure"` implementations.
        run = release_run(
            status="in_progress",
            conclusion=None,
            jobs=[gate_job(conclusion=None, status="in_progress")],
        )
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("gate-job-not-concluded", result.reason)
        expired = decide(payload(self_run(), run), ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, expired.decision)


class FreshnessTests(TestEnvContext):
    def test_success_predating_the_asking_run_does_not_grant(self):
        # delete + re-tag of the SAME sha: the OLD green run is still listed.
        stale = release_run(id=900, created_at=STALE_CREATED_AT)
        body = payload(self_run(), stale)
        result = decide(body, ctx())
        self.assertNotEqual(GRANT, result.decision)
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("stale-candidates-only", result.reason)
        self.assertEqual(1, result.facts["stale_candidates"])
        self.assertEqual(BLOCK, decide(body, ctx(now=NOW_PAST_DEADLINE)).decision)

    def test_fresh_rerun_wins_over_the_stale_success(self):
        stale = release_run(id=900, created_at=STALE_CREATED_AT)
        fresh_failure = release_run(
            id=901, created_at=CANDIDATE_CREATED_AT,
            conclusion="failure", jobs=[gate_job(conclusion="failure")],
        )
        result = decide(payload(self_run(), stale, fresh_failure), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-failure", result.reason)


class UsageTests(TestEnvContext):
    """A parameter that changes the verdict has no default (FIXER pass, W0).

    ``--self-created-at`` used to be optional with ``default=None`` — and
    ``None`` DISABLES the freshness floor, so omitting one flag turned the
    exact stale-success payload FreshnessTests rejects into a GRANT. Same
    class as F2's ``--today`` in ``_release_bump_sites.py``: the input that
    flips the verdict must be explicit or the run must refuse.
    """

    def _stale_only_body(self):
        # The delete+re-tag payload: ONLY a success predating the asking run.
        return json.dumps(payload(self_run(), release_run(id=900, created_at=STALE_CREATED_AT)))

    def test_omitting_self_created_at_refuses_instead_of_granting(self):
        proc = run_cli(self._stale_only_body(), self_created_at=None)
        self.assertNotEqual(
            EXIT_GRANT, proc.returncode,
            "omitting --self-created-at must never GRANT a stale success:\n" + proc.stdout,
        )
        self.assertEqual(EXIT_USAGE, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("--self-created-at", proc.stderr)

    def test_empty_self_created_at_is_a_usage_error_not_a_disabled_leg(self):
        # required=True alone would still let `--self-created-at ""` slip
        # through the old `if args.self_created_at:` truthiness parse-skip.
        proc = run_cli(self._stale_only_body(), self_created_at="")
        self.assertNotEqual(EXIT_GRANT, proc.returncode, proc.stdout)
        self.assertEqual(EXIT_USAGE, proc.returncode, proc.stdout + proc.stderr)


class ContextLayerTests(TestEnvContext):
    """W0 re-pass r2 P2: the CLI closed the fail-open default, but
    ``GateContext.self_created_at_epoch`` kept ``= None`` one layer down, and
    ``freshness_floor`` mapped None to "leg silently off" — any in-process
    caller of ``decide()`` reproduced the exact GRANT-on-stale-success the
    UsageTests prove the CLI refuses. The doctrine has to hold at EVERY
    construction surface, not just argparse."""

    def _stale_only_payload(self):
        return payload(self_run(), release_run(id=900, created_at=STALE_CREATED_AT))

    def test_gate_context_requires_self_created_at_epoch(self):
        # No default: an in-process caller that forgets the field cannot
        # construct a context at all — same failure mode as omitting the flag.
        with self.assertRaises(TypeError):
            GateContext(
                tag=TAG,
                head_sha=HEAD_SHA,
                now_epoch=NOW,
                deadline_epoch=DEADLINE_OPEN,
            )

    def test_explicit_none_fails_loud_instead_of_disarming_the_leg(self):
        # NamedTuple cannot stop an explicit None; it must refuse loudly,
        # never decide with the delete+re-tag freshness leg silently off.
        disarmed = GateContext(
            tag=TAG,
            head_sha=HEAD_SHA,
            now_epoch=NOW,
            self_created_at_epoch=None,
            deadline_epoch=DEADLINE_OPEN,
        )
        with self.assertRaises(ValueError):
            decide(self._stale_only_payload(), disarmed)


if __name__ == "__main__":
    unittest.main()
