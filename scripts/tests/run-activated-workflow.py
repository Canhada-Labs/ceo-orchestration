#!/usr/bin/env python3
"""run-activated-workflow.py — EXECUTE the `run:` steps of an ACTIVATED GitHub
Actions workflow inside a target checkout, the way the hosted runner would.

PLAN-183 W0-US3 / AC-5 (S337). The smoke install activates the delivered CI
template in a disposable target (scripts/tests/smoke-install.sh); this file is
the half that was missing: it RUNS the activated workflow instead of only
validating its shape. It is deliberately NOT a parallel battery — no check is
re-implemented here. Every command executed below is read verbatim from the
activated workflow file; what this file re-implements is only the runner's
dispatch loop, and only the subset the frozen template uses (11 steps, pinned
by .claude/scripts/tests/test_validate_template_frozen_subset.py):

  * steps run IN ORDER, each in its own ``bash --noprofile --norc -eo
    pipefail <script>`` (the runner's default shell for ``run:`` on Linux
    runners), cwd = the workspace, the job stops at the FIRST failing step;
  * ``uses:`` steps are runner-provided (checkout, setup-*) and are SKIPPED
    BY NAME on stdout — never silently;
  * the job-level ``if:`` must be the repository-variable kill switch the
    frozen template uses (``vars.X != '1'``) — reported and treated as
    "variable unset" (the job runs), which is what a fresh adopter
    repository has; any other expression is a parse failure;
  * the JOB-LEVEL keys are whitelisted (name, runs-on, if, timeout-minutes,
    steps) and ``runs-on`` must be an ubuntu runner: a job that gains
    ``env:``/``container:``/``strategy:``/``defaults:`` or moves off ubuntu
    fails the parse instead of executing under silently different local
    semantics (rail r2, S337), and the WORKFLOW-LEVEL keys are whitelisted
    too — name, on, concurrency, permissions, jobs; a top-level ``env:`` or
    ``defaults:`` is a parse failure (rail r3, S337);
  * the job-level ``timeout-minutes`` is HONOURED as a wall-clock deadline
    over the whole job (rail r1, S337): a step still running when it expires
    is killed and the job FAILS, exactly as the hosted runner cancels it —
    otherwise a step that takes 20 minutes would pass here and be cancelled
    on GitHub. Default when absent: 360 minutes (the hosted default);
  * runner environment: ``GITHUB_WORKSPACE`` = the workspace, ``RUNNER_TEMP``
    = a fresh temp dir, ``CI`` / ``GITHUB_ACTIONS`` = ``true``, ``RUNNER_OS``
    per platform.

Anything OUTSIDE that subset — a step-level ``if:``, ``shell:``,
``working-directory:``, ``env:``, ``continue-on-error:``, a step-level
``timeout-minutes:``, a second job, a step with neither ``uses:`` nor
``run:`` — is a parse failure (exit 2), not a guess. A template that outgrows
this parser must surface as a failure, never as a vacuous pass (CLAUDE.md §5:
"instrumento verde cuja PERGUNTA envelheceu").

stdlib only: PyYAML is a third-party module and the framework runtime is
stdlib-only (CLAUDE.md §4), so the parser reads the frozen template's YAML
shape (block-scalar ``run: |``, single-line ``run:``, ``uses:``) directly.

Usage:
    run-activated-workflow.py <workspace> <workflow-relpath> [--list]

Exit codes:
    0  every ``run:`` step passed (and at least one ran)
    1  a ``run:`` step failed, or the job deadline expired (name printed)
    2  usage / parse failure (unsupported shape, no job, no run step)
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional, Tuple

# Keys a step may carry, and what each one means to this runner.
_STEP_KEYS_SUPPORTED = ("name", "uses", "run", "with")
# Job-level keys this runner models. Anything else (env:, defaults:,
# container:, strategy:, services:, permissions: …) changes execution
# semantics the local dispatch loop does not reproduce — parse failure, not a
# silent local approximation (rail r2, S337).
_JOB_KEYS_SUPPORTED = ("name", "runs-on", "if", "timeout-minutes", "steps")
# Workflow-level keys this runner models. `on:` and `concurrency:` govern WHEN
# the hosted job runs (trigger plumbing — execution-neutral here); a top-level
# `permissions:` only RESTRICTS the token. `env:` or `defaults:` would change
# the environment/shell semantics of every step — parse failure (rail r3).
_TOP_KEYS_SUPPORTED = ("name", "on", "concurrency", "permissions", "jobs")
# The one job-level `if:` shape the frozen template uses: a repository-variable
# kill switch. Any other expression would need the Actions expression engine.
_JOB_IF_SHAPE = re.compile(r"vars\.[A-Za-z_][A-Za-z0-9_]*\s*!=\s*'1'")
_STEP_KEYS_UNSUPPORTED = (
    "if", "shell", "working-directory", "env", "continue-on-error",
    "timeout-minutes", "id",
)
_DEFAULT_JOB_TIMEOUT_MIN = 360  # the hosted runner's default


class ParseError(Exception):
    pass


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank_or_comment(line: str) -> bool:
    s = line.strip()
    return not s or s.startswith("#")


def _find_key_line(lines: List[str], key: str, indent: int, start: int, stop: int) -> Optional[int]:
    """Index of the first line in [start, stop) that is ``key:`` at exactly ``indent``."""
    pat = re.compile(r"^ {%d}%s:(\s|$)" % (indent, re.escape(key)))
    for i in range(start, stop):
        if pat.match(lines[i]):
            return i
    return None


def _block_end(lines: List[str], start: int, indent: int) -> int:
    """First index after ``start`` whose content is at indent <= ``indent``
    (blank/comment lines never end a block)."""
    i = start + 1
    while i < len(lines):
        if not _is_blank_or_comment(lines[i]) and _indent(lines[i]) <= indent:
            return i
        i += 1
    return len(lines)


def _scalar_value(lines: List[str], idx: int, key_indent: int) -> Tuple[str, int]:
    """Value of the scalar at ``lines[idx]`` (``key: value`` or ``key: |``
    block). Returns (value, index_after)."""
    line = lines[idx]
    after = line.split(":", 1)[1]
    stripped = after.strip()
    end = _block_end(lines, idx, key_indent)
    if stripped in ("|", "|-", "|+", ">", ">-"):
        if stripped.startswith(">"):
            # Folded scalars are not used by the frozen template; refuse
            # rather than approximate the folding rules.
            raise ParseError("folded scalar (>) at line %d is not supported" % (idx + 1))
        body = lines[idx + 1:end]
        content = [l for l in body if l.strip()]
        if not content:
            raise ParseError("empty block scalar at line %d" % (idx + 1))
        base = min(_indent(l) for l in content)
        out = []
        for l in body:
            out.append(l[base:] if len(l) >= base else "")
        return "\n".join(out).rstrip("\n") + "\n", end
    if stripped == "":
        raise ParseError("key at line %d has no value" % (idx + 1))
    if stripped[0] in "\"'" and stripped[-1] == stripped[0] and len(stripped) >= 2:
        stripped = stripped[1:-1]
    return stripped + "\n", idx + 1


def _job_scalar(lines: List[str], key: str, indent: int, start: int, stop: int) -> Optional[str]:
    idx = _find_key_line(lines, key, indent, start, stop)
    if idx is None:
        return None
    return lines[idx].split(":", 1)[1].strip()


def parse_workflow(text: str) -> Dict[str, object]:
    lines = text.splitlines()
    n = len(lines)

    # rail r3 (S337): whitelist the WORKFLOW-LEVEL keys before anything else —
    # a top-level env:/defaults: changes every step, and skipping straight to
    # jobs: would execute under silently different semantics.
    for i in range(0, n):
        if _is_blank_or_comment(lines[i]) or _indent(lines[i]) != 0:
            continue
        m = re.match(r"^([A-Za-z-]+):", lines[i])
        if not m:
            raise ParseError("unexpected top-level line at %d: %r" % (i + 1, lines[i]))
        if m.group(1) not in _TOP_KEYS_SUPPORTED:
            raise ParseError("workflow uses top-level `%s:` (line %d), which this runner does not model" % (
                m.group(1), i + 1))

    jobs_idx = _find_key_line(lines, "jobs", 0, 0, n)
    if jobs_idx is None:
        raise ParseError("no top-level `jobs:` key")
    jobs_end = _block_end(lines, jobs_idx, 0)

    # Job ids: first-level children of jobs:.
    job_ids: List[Tuple[int, str]] = []
    job_indent = None
    for i in range(jobs_idx + 1, jobs_end):
        if _is_blank_or_comment(lines[i]):
            continue
        ind = _indent(lines[i])
        if job_indent is None:
            job_indent = ind
        if ind == job_indent:
            m = re.match(r"^ *([A-Za-z_][A-Za-z0-9_-]*):\s*$", lines[i])
            if not m:
                raise ParseError("unexpected line under jobs: at %d: %r" % (i + 1, lines[i]))
            job_ids.append((i, m.group(1)))
    if len(job_ids) != 1:
        raise ParseError("expected exactly one job, found %d (%s)" % (
            len(job_ids), ", ".join(j for _, j in job_ids)))
    job_idx, job_id = job_ids[0]
    assert job_indent is not None
    job_end = _block_end(lines, job_idx, job_indent)
    body_indent = job_indent + 2

    # rail r2 (S337): whitelist the JOB-LEVEL keys before reading any of them —
    # a job that gains env:/container:/strategy:/defaults: must fail the parse,
    # never execute under a silently different local environment.
    for i in range(job_idx + 1, job_end):
        if _is_blank_or_comment(lines[i]) or _indent(lines[i]) != body_indent:
            continue
        m = re.match(r"^ *([A-Za-z-]+):", lines[i])
        if not m:
            raise ParseError("unexpected line in job body at %d: %r" % (i + 1, lines[i]))
        if m.group(1) not in _JOB_KEYS_SUPPORTED:
            raise ParseError("job %r uses `%s:` (line %d), which this runner does not model" % (
                job_id, m.group(1), i + 1))

    runs_on = _job_scalar(lines, "runs-on", body_indent, job_idx + 1, job_end)
    if runs_on is None or not runs_on.startswith("ubuntu-"):
        raise ParseError("job %r runs-on %r — this local runner only models ubuntu runners" % (
            job_id, runs_on))

    job_if = _job_scalar(lines, "if", body_indent, job_idx + 1, job_end)
    if job_if is not None:
        stripped_if = job_if.strip()
        if stripped_if.startswith("${{") and stripped_if.endswith("}}"):
            stripped_if = stripped_if[3:-2].strip()
        if not _JOB_IF_SHAPE.fullmatch(stripped_if):
            raise ParseError("job %r has an if: expression this runner does not model: %r" % (
                job_id, job_if))

    timeout_raw = _job_scalar(lines, "timeout-minutes", body_indent, job_idx + 1, job_end)
    if timeout_raw is None:
        job_timeout_min = _DEFAULT_JOB_TIMEOUT_MIN
    else:
        if not re.fullmatch(r"[0-9]+", timeout_raw) or int(timeout_raw) <= 0:
            raise ParseError("job %r has a non-integer timeout-minutes: %r" % (job_id, timeout_raw))
        job_timeout_min = int(timeout_raw)

    steps_idx = _find_key_line(lines, "steps", body_indent, job_idx + 1, job_end)
    if steps_idx is None:
        raise ParseError("job %r has no steps:" % job_id)
    steps_end = _block_end(lines, steps_idx, body_indent)

    # Step items: `- name:` lines at the item indent (first item defines it).
    item_indent = None
    item_starts: List[int] = []
    for i in range(steps_idx + 1, steps_end):
        if _is_blank_or_comment(lines[i]):
            continue
        ind = _indent(lines[i])
        if item_indent is None:
            item_indent = ind
        if ind == item_indent:
            if not re.match(r"^ *- name:\s*\S", lines[i]):
                raise ParseError("step item at line %d does not start with `- name:`: %r" % (i + 1, lines[i]))
            item_starts.append(i)
        elif ind < item_indent:
            raise ParseError("dedent inside steps at line %d" % (i + 1))
    if not item_starts:
        raise ParseError("job %r has an empty steps: list" % job_id)
    assert item_indent is not None
    key_indent = item_indent + 2

    steps: List[Dict[str, object]] = []
    for k, s in enumerate(item_starts):
        e = item_starts[k + 1] if k + 1 < len(item_starts) else steps_end
        name = lines[s].split(":", 1)[1].strip()
        if name[:1] in "\"'" and name[-1:] == name[:1] and len(name) >= 2:
            name = name[1:-1]
        keys: Dict[str, int] = {}
        i = s + 1
        while i < e:
            if _is_blank_or_comment(lines[i]):
                i += 1
                continue
            if _indent(lines[i]) != key_indent:
                raise ParseError("unexpected indentation inside step %r at line %d: %r" % (name, i + 1, lines[i]))
            m = re.match(r"^ *([A-Za-z_-]+):", lines[i])
            if not m:
                raise ParseError("unexpected line inside step %r at line %d: %r" % (name, i + 1, lines[i]))
            key = m.group(1)
            if key in _STEP_KEYS_UNSUPPORTED:
                raise ParseError("step %r uses `%s:` (line %d), which this runner does not model" % (name, key, i + 1))
            if key not in _STEP_KEYS_SUPPORTED:
                raise ParseError("step %r uses unknown key `%s:` (line %d)" % (name, key, i + 1))
            if key in keys:
                raise ParseError("step %r repeats key `%s:` (line %d)" % (name, key, i + 1))
            keys[key] = i
            i = _block_end(lines, i, key_indent)
        has_uses = "uses" in keys
        has_run = "run" in keys
        if has_uses == has_run:
            raise ParseError("step %r must have exactly one of uses:/run:" % name)
        if "with" in keys and not has_uses:
            raise ParseError("step %r has with: without uses:" % name)
        if has_uses:
            uses, _ = _scalar_value(lines, keys["uses"], key_indent)
            steps.append({"name": name, "kind": "uses", "uses": uses.strip()})
        else:
            script, _ = _scalar_value(lines, keys["run"], key_indent)
            steps.append({"name": name, "kind": "run", "script": script})

    return {"job_id": job_id, "job_if": job_if, "timeout_min": job_timeout_min, "steps": steps}


def _runner_env(workspace: str, runner_temp: str) -> Dict[str, str]:
    env = dict(os.environ)
    env.update({
        "GITHUB_WORKSPACE": workspace,
        "RUNNER_TEMP": runner_temp,
        "RUNNER_TOOL_CACHE": runner_temp,
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": {"Linux": "Linux", "Darwin": "macOS", "Windows": "Windows"}.get(
            platform.system(), platform.system()),
    })
    return env


def main(argv: List[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 2 or flags - {"--list"}:
        sys.stderr.write(__doc__.split("Usage:", 1)[1].split("Exit codes:", 1)[0])
        return 2
    workspace = os.path.realpath(args[0])
    wf_rel = args[1]
    wf_path = os.path.join(workspace, wf_rel)
    if not os.path.isdir(workspace):
        sys.stderr.write("run-activated-workflow: workspace is not a directory: %s\n" % workspace)
        return 2
    if wf_rel.endswith(".template"):
        sys.stderr.write("run-activated-workflow: refusing a .template — activate it first (the adopter's mv)\n")
        return 2
    if not os.path.isfile(wf_path):
        sys.stderr.write("run-activated-workflow: workflow not found: %s\n" % wf_path)
        return 2

    try:
        with open(wf_path, encoding="utf-8") as fh:
            wf = parse_workflow(fh.read())
    except ParseError as exc:
        sys.stderr.write("run-activated-workflow: PARSE FAILURE in %s: %s\n" % (wf_rel, exc))
        return 2

    steps = wf["steps"]  # type: ignore[assignment]
    assert isinstance(steps, list)
    timeout_min = int(wf["timeout_min"])  # type: ignore[arg-type]
    run_steps = [s for s in steps if s["kind"] == "run"]
    print("==> activated workflow: %s (job %r, %d steps: %d run, %d uses; timeout-minutes %d)" % (
        wf_rel, wf["job_id"], len(steps), len(run_steps), len(steps) - len(run_steps), timeout_min))
    if wf["job_if"]:
        print("    job-level if: %s — treated as unset repository variable (job runs)" % wf["job_if"])
    if not run_steps:
        sys.stderr.write("run-activated-workflow: no run: step — nothing would execute (refusing a vacuous pass)\n")
        return 2

    if "--list" in flags:
        for i, s in enumerate(steps, 1):
            if s["kind"] == "uses":
                print("  %2d. [uses] %s  (%s)" % (i, s["name"], s["uses"]))
            else:
                first = str(s["script"]).strip().splitlines()[0]
                print("  %2d. [run ] %s  (%s%s)" % (i, s["name"], first[:60], "…" if len(first) > 60 else ""))
        return 0

    runner_temp = tempfile.mkdtemp(prefix="runner-temp-")
    env = _runner_env(workspace, runner_temp)
    total = len(steps)
    deadline = time.monotonic() + timeout_min * 60.0
    for i, s in enumerate(steps, 1):
        name = str(s["name"])
        if s["kind"] == "uses":
            print("==> step %d/%d: %s — SKIPPED (runner-provided: uses: %s)" % (i, total, name, s["uses"]))
            sys.stdout.flush()
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("    FAIL: job timeout-minutes %d expired before step %d/%d %r — the hosted runner would have cancelled the job" % (
                timeout_min, i, total, name))
            return 1
        print("==> step %d/%d: %s" % (i, total, name))
        sys.stdout.flush()
        fd, script_path = tempfile.mkstemp(prefix="step-", suffix=".sh", dir=runner_temp)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(s["script"]))
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                ["bash", "--noprofile", "--norc", "-eo", "pipefail", script_path],
                cwd=workspace, env=env, timeout=remaining,
            )
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            print("    FAIL: job timeout-minutes %d expired during step %d/%d %r (%.0fs in) — killed, as the hosted runner would cancel it" % (
                timeout_min, i, total, name, time.monotonic() - t0))
            return 1
        except OSError as exc:
            print("    FAIL: could not start bash: %s" % exc)
            return 1
        dt = time.monotonic() - t0
        if rc != 0:
            print("    FAIL: step %d/%d %r exited rc=%d after %.1fs — the adopter's CI would be RED here" % (
                i, total, name, rc, dt))
            return 1
        print("    ok (%.1fs)" % dt)
        sys.stdout.flush()
    print("==> activated workflow PASSED: %d run step(s) executed, %d runner-provided step(s) skipped by name" % (
        len(run_steps), total - len(run_steps)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
