#!/usr/bin/env python3
"""await_release_gate.py — PLAN-166 W0 item 6 (F1): decision function that
tells ``npm-publish.yml`` whether the ``release.yml`` **release-gate** job
actually passed for *this* tag, at *this* commit, in *this* push.

## The bug this closes (F1, P0)

``npm-publish.yml`` and ``release.yml`` both fire on ``push: tags: v*``.
They are INDEPENDENT runs — nothing made the publish observe the gate. The
only barrier was the ``production-npm`` environment approval, i.e. a human
clicking "approve" with no machine evidence that the governance gate was
even green. That is a live path to publishing an unreviewed tree.

## Contract

Pure, offline, stdlib-only. Input is the JSON the caller already fetched
(``gh api .../actions/runs?head_sha=...`` merged with each run's
``.../jobs``); output is exactly one of three decisions **per evaluation
point** (the caller polls; each poll is one independent decision):

* ``GRANT`` — only when ONE run satisfies EVERY condition simultaneously:
  workflow file ``release.yml``, ``event == "push"``,
  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
  (see below), and its **job** ``release-gate`` has
  ``conclusion == "success"``. Never the RUN conclusion: ``release.yml``
  carries ``if: vars.CEO_SOTA_DISABLE != '1'`` on ``release-gate``, so a
  disabled gate SKIPS the job while the run itself stays green. Reading the
  run conclusion would grant on a gate that never executed.

* ``WAIT`` — evidence is legitimately not in yet and the deadline has not
  passed: (a) no candidate run yet — workflows from the same push start in
  ARBITRARY order, absence is neither failure nor permission; (b) the
  candidate run exists but the ``release-gate`` job has not materialised in
  the jobs endpoint yet (eventual consistency — without this state a
  "BLOCK on mismatch" rule produces an instant false block in the rc.2/GA
  race); (c) the job exists with ``conclusion: null`` (queued/running).

* ``BLOCK`` — fail-CLOSED: the candidate's gate job concluded anything
  other than ``success`` (``failure``, ``skipped``, ``cancelled``, …),
  malformed JSON, an API error payload, or **the deadline elapsed in ANY
  non-GRANT state**. Per ADR-186 this is INPUT verification, not
  infrastructure: content we cannot verify is blocked, not waved through.

## Candidate semantics (load-bearing — do not "optimise" this away)

The head-SHA run list contains UNRELATED runs, **including the npm-publish
run doing the asking**. Non-candidate runs are IGNORED — never BLOCK.
"Mismatch" is only ever evaluated against the exact candidate
(workflow + tag + SHA + event). If any near-miss run could BLOCK, every
release would lose the race against its own presence in the list.

## Freshness (delete + re-tag of the SAME sha)

Re-tagging the same commit leaves the OLD Release run in the list with the
same ``head_sha``/``head_branch``. Polling before the NEW Release run is
created would otherwise find the old ``success`` as "most recent" and grant
— even if the new run later fails. So a candidate must have been created no
earlier than the asking run's own creation, minus ``--freshness-skew-seconds``
(default 120s) to absorb same-push jitter: both workflows are created by one
push event, and their ``created_at`` ordering is arbitrary within seconds.
Runs older than that window are not candidates at all (→ WAIT, then BLOCK at
the deadline). KNOWN LIMIT, stated rather than hidden: a delete+re-tag
completed FASTER than the skew window can still admit the previous run; the
skew is a jitter allowance, not a proof, and it is printed with every
decision so the value used is auditable.

``--self-created-at`` is REQUIRED. It is the input that switches this whole
leg on, so it gets no default: omitting it (or passing an empty/unparseable
value) is a usage error (exit 2), never a run that silently grants stale
successes. Same doctrine as ``_release_bump_sites.py --today``: a parameter
that changes the verdict has no default.

## Required fields per run object

``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
``created_at``, optional ``run_attempt``/``id`` (tie-break), and ``jobs``
(a list, or the raw ``{"jobs": [...]}`` envelope). A run with no ``path``
cannot be attributed to a workflow and is therefore not a candidate.

## Usage

    python3 .claude/scripts/await_release_gate.py \
        --payload-file runs.json --tag v1.3.0 --head-sha "$GITHUB_SHA" \
        --self-created-at "$SELF_CREATED_AT" --deadline-epoch "$DEADLINE"

``--payload-file -`` reads stdin.

Exit codes:
    0 — GRANT   (publish may proceed)
    1 — BLOCK   (fail-closed; caller must fail the job)
    2 — usage error (bad arguments)
    3 — WAIT    (caller sleeps and polls again)
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
import time
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

GRANT = "GRANT"
WAIT = "WAIT"
BLOCK = "BLOCK"

EXIT_GRANT = 0
EXIT_BLOCK = 1
EXIT_USAGE = 2
EXIT_WAIT = 3

_EXIT_BY_DECISION = {GRANT: EXIT_GRANT, BLOCK: EXIT_BLOCK, WAIT: EXIT_WAIT}

DEFAULT_WORKFLOW = "release.yml"
DEFAULT_GATE_JOB = "release-gate"
DEFAULT_EVENT = "push"
DEFAULT_FRESHNESS_SKEW_SECONDS = 120


class MalformedPayload(Exception):
    """Input we cannot parse — fail-CLOSED (BLOCK), never ignore."""


class GateContext(NamedTuple):
    """Every input the decision depends on. Printed with every decision."""

    tag: str
    head_sha: str
    now_epoch: int
    workflow: str = DEFAULT_WORKFLOW
    gate_job: str = DEFAULT_GATE_JOB
    event: str = DEFAULT_EVENT
    deadline_epoch: Optional[int] = None
    self_created_at_epoch: Optional[int] = None
    freshness_skew_seconds: int = DEFAULT_FRESHNESS_SKEW_SECONDS

    @property
    def deadline_passed(self) -> bool:
        return self.deadline_epoch is not None and self.now_epoch > self.deadline_epoch

    @property
    def freshness_floor(self) -> Optional[int]:
        if self.self_created_at_epoch is None:
            return None
        return self.self_created_at_epoch - self.freshness_skew_seconds


class Decision(NamedTuple):
    decision: str
    reason: str
    facts: Dict[str, Any]

    @property
    def exit_code(self) -> int:
        return _EXIT_BY_DECISION[self.decision]


_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})"
    r"(?:\.\d+)?(Z|z|[+-]\d{2}:?\d{2})?$"
)


def parse_timestamp(raw: Any) -> Optional[int]:
    """ISO-8601 (GitHub flavour) -> epoch seconds UTC. ``None`` if unparseable.

    ``datetime.fromisoformat`` cannot read a trailing ``Z`` on Python 3.9, so
    this parses explicitly instead of depending on interpreter version.
    """
    if not isinstance(raw, str):
        return None
    m = _TS_RE.match(raw.strip())
    if m is None:
        return None
    parts = [int(m.group(i)) for i in range(1, 7)]
    try:
        epoch = calendar.timegm(
            (parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], 0, 1, -1)
        )
    except (ValueError, OverflowError):
        return None
    off = m.group(7)
    if off and off not in ("Z", "z"):
        sign = 1 if off[0] == "+" else -1
        digits = off[1:].replace(":", "")
        epoch -= sign * (int(digits[:2]) * 3600 + int(digits[2:4]) * 60)
    return epoch


def extract_runs(payload: Any) -> List[Dict[str, Any]]:
    """Pull the run list out of the payload, or raise MalformedPayload.

    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
    list. An API error body (``{"message": "Bad credentials", ...}``) has
    neither key and therefore raises — BLOCK, by design.
    """
    if not isinstance(payload, dict):
        raise MalformedPayload("payload is %s, expected a JSON object" % type(payload).__name__)
    for key in ("workflow_runs", "runs"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, list):
                raise MalformedPayload("payload['%s'] is not a list" % key)
            for item in value:
                if not isinstance(item, dict):
                    raise MalformedPayload("payload['%s'] holds a non-object entry" % key)
            return value
    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")


def _workflow_file(run: Dict[str, Any]) -> Optional[str]:
    for key in ("path", "workflow_path"):
        value = run.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().rsplit("/", 1)[-1]
    return None


def _same_sha(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return left.strip().lower() == right.strip().lower()


def is_identity_match(run: Dict[str, Any], ctx: GateContext) -> bool:
    """workflow + event + tag + head_sha, all four, no partial credit."""
    return (
        _workflow_file(run) == ctx.workflow
        and run.get("event") == ctx.event
        and run.get("head_branch") == ctx.tag
        and _same_sha(run.get("head_sha"), ctx.head_sha)
    )


def _sort_key(run: Dict[str, Any], created_at: int) -> Tuple[int, int, int]:
    attempt = run.get("run_attempt")
    run_id = run.get("id")
    return (
        created_at,
        attempt if isinstance(attempt, int) else 0,
        run_id if isinstance(run_id, int) else 0,
    )


def select_candidate(
    runs: Sequence[Dict[str, Any]], ctx: GateContext
) -> Tuple[Optional[Dict[str, Any]], Dict[str, int]]:
    """Most recent FRESH identity-matching run, plus a census of what was seen.

    Raises MalformedPayload when an identity-matching run carries a
    ``created_at`` we cannot parse: a candidate we cannot date cannot be
    proven fresh, and unverifiable input is fail-CLOSED.
    """
    census = {"runs_total": len(runs), "identity_matches": 0, "stale_candidates": 0}
    best: Optional[Dict[str, Any]] = None
    best_key: Optional[Tuple[int, int, int]] = None
    floor = ctx.freshness_floor
    for run in runs:
        if not is_identity_match(run, ctx):
            continue
        census["identity_matches"] += 1
        created_at = parse_timestamp(run.get("created_at"))
        if created_at is None:
            raise MalformedPayload(
                "candidate run id=%r has an unparseable created_at=%r"
                % (run.get("id"), run.get("created_at"))
            )
        if floor is not None and created_at < floor:
            census["stale_candidates"] += 1
            continue
        key = _sort_key(run, created_at)
        if best_key is None or key > best_key:
            best, best_key = run, key
    census["fresh_candidates"] = census["identity_matches"] - census["stale_candidates"]
    return best, census


def find_gate_job(run: Dict[str, Any], gate_job: str) -> Optional[Dict[str, Any]]:
    """The ``release-gate`` job inside a run, or None if not materialised yet."""
    jobs = run.get("jobs")
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs")
    if not isinstance(jobs, list):
        return None
    for job in jobs:
        if isinstance(job, dict) and job.get("name") == gate_job:
            return job
    return None


def _wait_or_block(reason: str, ctx: GateContext, facts: Dict[str, Any]) -> Decision:
    """Every non-GRANT state collapses to BLOCK once the deadline elapses."""
    if ctx.deadline_passed:
        return Decision(BLOCK, "deadline-exceeded:" + reason, facts)
    return Decision(WAIT, reason, facts)


def _candidate_facts(run: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_run_id": run.get("id"),
        "candidate_run_attempt": run.get("run_attempt"),
        "candidate_created_at": run.get("created_at"),
        "candidate_run_status": run.get("status"),
        "candidate_run_conclusion": run.get("conclusion"),
    }


def decide(payload: Any, ctx: GateContext) -> Decision:
    """The whole decision. Pure: no network, no clock, no filesystem."""
    facts: Dict[str, Any] = {}
    try:
        runs = extract_runs(payload)
        candidate, census = select_candidate(runs, ctx)
    except MalformedPayload as exc:
        facts["error"] = str(exc)
        return Decision(BLOCK, "malformed-payload", facts)
    facts.update(census)
    if candidate is None:
        reason = "stale-candidates-only" if census["stale_candidates"] else "candidate-not-yet-created"
        return _wait_or_block(reason, ctx, facts)
    facts.update(_candidate_facts(candidate))
    job = find_gate_job(candidate, ctx.gate_job)
    if job is None:
        facts["gate_job_present"] = False
        return _wait_or_block("gate-job-not-materialised", ctx, facts)
    facts["gate_job_present"] = True
    facts["gate_job_status"] = job.get("status")
    conclusion = job.get("conclusion")
    facts["gate_job_conclusion"] = conclusion
    if conclusion is None:
        return _wait_or_block("gate-job-not-concluded", ctx, facts)
    if not isinstance(conclusion, str):
        facts["error"] = "gate job conclusion is %s, expected string or null" % type(conclusion).__name__
        return Decision(BLOCK, "malformed-payload", facts)
    if conclusion == "success":
        return Decision(GRANT, "gate-job-success", facts)
    return Decision(BLOCK, "gate-job-" + conclusion, facts)


def render(decision: Decision, ctx: GateContext) -> str:
    """Human-readable record. A decision that hides its inputs is unauditable."""
    remaining = "n/a"
    if ctx.deadline_epoch is not None:
        remaining = str(ctx.deadline_epoch - ctx.now_epoch)
    lines = [
        "decision=%s reason=%s" % (decision.decision, decision.reason),
        "inputs: workflow=%s gate_job=%s event=%s tag=%s head_sha=%s"
        % (ctx.workflow, ctx.gate_job, ctx.event, ctx.tag, ctx.head_sha),
        "inputs: now_epoch=%s deadline_epoch=%s deadline_remaining_s=%s"
        % (ctx.now_epoch, ctx.deadline_epoch, remaining),
        "inputs: self_created_at_epoch=%s freshness_skew_s=%s freshness_floor_epoch=%s"
        % (ctx.self_created_at_epoch, ctx.freshness_skew_seconds, ctx.freshness_floor),
    ]
    for key in sorted(decision.facts):
        lines.append("fact: %s=%r" % (key, decision.facts[key]))
    return "\n".join(lines)


def _load_payload(path: str) -> Any:
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    return json.loads(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decide whether release-gate authorises an npm publish.")
    parser.add_argument("--payload-file", default="-", help="JSON of runs+jobs ('-' = stdin)")
    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
    parser.add_argument("--head-sha", required=True, help="GITHUB_SHA the publish is running against")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--gate-job", default=DEFAULT_GATE_JOB)
    parser.add_argument("--event", default=DEFAULT_EVENT)
    parser.add_argument(
        "--deadline-epoch",
        type=int,
        required=True,
        help="epoch seconds after which any non-GRANT state becomes BLOCK (fail-closed)",
    )
    parser.add_argument("--now-epoch", type=int, default=None, help="override the clock (tests)")
    parser.add_argument(
        "--self-created-at",
        required=True,
        help=(
            "created_at of the ASKING run; candidates older than this minus "
            "the skew are stale. Required: this input arms the delete+re-tag "
            "freshness leg, and a verdict-changing parameter has no default"
        ),
    )
    parser.add_argument(
        "--freshness-skew-seconds", type=int, default=DEFAULT_FRESHNESS_SKEW_SECONDS
    )
    parser.add_argument("--json", action="store_true", help="emit the decision record as JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Unconditional parse: `required=True` rejects the OMITTED flag, and this
    # rejects the empty/garbage value that a truthiness guard would have
    # silently mapped to "freshness leg off".
    self_created_at_epoch = parse_timestamp(args.self_created_at)
    if self_created_at_epoch is None:
        sys.stderr.write(
            "error: --self-created-at %r is not an ISO-8601 timestamp "
            "(the freshness leg cannot run without it)\n" % args.self_created_at
        )
        return EXIT_USAGE
    ctx = GateContext(
        tag=args.tag,
        head_sha=args.head_sha,
        now_epoch=args.now_epoch if args.now_epoch is not None else int(time.time()),
        workflow=args.workflow,
        gate_job=args.gate_job,
        event=args.event,
        deadline_epoch=args.deadline_epoch,
        self_created_at_epoch=self_created_at_epoch,
        freshness_skew_seconds=args.freshness_skew_seconds,
    )
    try:
        payload = _load_payload(args.payload_file)
    except (OSError, ValueError) as exc:
        decision = Decision(BLOCK, "malformed-payload", {"error": str(exc)})
    else:
        decision = decide(payload, ctx)
    if args.json:
        print(json.dumps({
            "decision": decision.decision,
            "reason": decision.reason,
            "facts": decision.facts,
            "inputs": ctx._asdict(),
        }, sort_keys=True, default=str))
    else:
        print(render(decision, ctx))
    return decision.exit_code


if __name__ == "__main__":
    sys.exit(main())
