#!/usr/bin/env python3
"""ceo-launches.py — read and reuse the Workflow launch ledger (PLAN-190 W1).

The ledger is written by ``.claude/hooks/check_workflow_launch.py`` before every
``Workflow`` tool call; this CLI is how an operator (or a consumer's recovery
rite) gets the EXACT recorded call back instead of rebuilding it from memory.

Commands::

    ceo-launches.py list [--limit N]            recent launches (id, run, resume, guard, bind method)
    ceo-launches.py show <launch_id|run_id>     the full manifest (args printed as literal JSON)
    ceo-launches.py relaunch <run_id> [--out FILE]
                                                the exact call to re-issue: the script SNAPSHOT (bytes
                                                recorded before dispatch — pass it as scriptPath) + args literal;
                                                rc 7 and NOTHING printed as exact when the record fails its
                                                integrity check (snapshot hash, args canonical/hash)
    ceo-launches.py check --run <run_id> [--script-file F | --script-text F] [--args-file F | --no-args]
                                                the guard's comparison, standalone: rc 0 same, rc 3 args differ,
                                                rc 5 script differs (args same), rc 6 inconclusive (unavailable hash
                                                or a record that fails its integrity check), rc 4 no manifest
    ceo-launches.py bind <launch_id> <run_id>   manual binding of an orphan (run id validated by shape)
    ceo-launches.py orphans                     run ids seen in responses that could not be bound
    ceo-launches.py report                      counts by guard result, bind method, orphans (W0.2 groundwork)

A deliberate resume over different inputs is declared IN THE CALL, not with this CLI: a
``description`` that starts with ``CEO_WORKFLOW_RESUME_FORCE: <why>`` (see
docs/workflow-recovery.md). Nothing is stored for it, so nothing can be replayed.

Stdlib only, Python >= 3.9. Read-only except ``bind`` and ``relaunch --out``.
Never prints transcript content; ``args`` are the operator's own inputs.
``--project-dir`` overrides the runtime state dir resolution (same resolver as the hooks).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve()
_HOOKS_DIR = _HERE.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import launch_ledger as LL  # noqa: E402


def _project_root_from_cwd() -> Optional[Path]:
    """Nearest ancestor of cwd (cwd included) holding a ``.claude/`` directory, excluding
    ``$HOME`` itself (``~/.claude`` is the global config, not a project). Absolutized, not
    realpath'd — the same symlink honesty as ``runtime_paths.project_dir``."""
    home = os.path.abspath(os.environ.get("HOME") or os.path.expanduser("~"))
    start = Path(os.path.abspath(os.getcwd()))
    for p in (start,) + tuple(start.parents):
        if str(p) == home:
            continue
        if (p / ".claude").is_dir():
            return p
    return None


def _dir(args: argparse.Namespace) -> Path:
    """``--project-dir`` (a state dir root) wins; else the resolver the hooks use —
    ``CLAUDE_PROJECT_DIR`` when the harness set it, otherwise the project found by walking
    up from cwd, so the CLI run from a subdirectory reads the ledger the hook wrote."""
    if args.project_dir:
        return LL.ledger_dir(Path(os.path.expanduser(args.project_dir)))
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR_NATIVE"):
        return LL.ledger_dir()
    from _lib import runtime_paths  # noqa: E402

    root = _project_root_from_cwd()
    return LL.ledger_dir(runtime_paths.runtime_state_dir(root) if root is not None else None)


def _resolve(d: Path, ident: str) -> Optional[Dict[str, Any]]:
    if ident.startswith("L-"):
        return LL.load_manifest(d, ident)
    if not LL.is_run_id(ident):
        return None
    return LL.find_launch_for_run(d, ident)


def cmd_list(args: argparse.Namespace) -> int:
    d = _dir(args)
    lines = [ln for ln in LL.iter_index(d) if ln.get("kind") == "launch"]
    print("%-28s %-18s %-18s %-26s %-16s %-12s %-12s" % ("launch_id", "run_id", "resume_from", "guard", "bind", "script", "args"))
    for ln in lines[-args.limit:]:
        m = LL.load_manifest(d, ln["launch_id"]) or {}
        print("%-28s %-18s %-18s %-26s %-16s %-12s %-12s" % (
            ln["launch_id"], m.get("run_id") or "-", ln.get("resume_from_run_id") or "-",
            (m.get("guard") or {}).get("result", "?"), m.get("bind_method") or "-",
            (ln.get("script_sha256") or "none")[:12], (ln.get("args_sha256") or "none")[:12]))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    d = _dir(args)
    m = _resolve(d, args.ident)
    if m is None:
        print("no manifest for %s" % args.ident, file=sys.stderr)
        return 4
    print(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


def _write_new_file(path: str, data: bytes) -> Optional[str]:
    """Create ``path`` with ``data``; never overwrite, never follow a symlink. Returns an error text or None."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return "refused: %s already exists (relaunch --out never overwrites)" % path
    except (OSError, ValueError) as exc:
        return "refused: cannot create %s (%s)" % (path, type(exc).__name__)
    # ``os.write`` may write FEWER bytes than asked: loop until every byte is down.
    # A truncated copy here is the exact material the recovery rite passes back as
    # ``scriptPath`` — so it is the whole file or no file (PLAN-190 W1.1).
    written = 0
    failure: Optional[str] = None
    ours = None
    try:
        ours = os.fstat(fd)
        view = memoryview(data)
        while written < len(data):
            try:
                n = os.write(fd, view[written:])
            except InterruptedError:
                continue
            if n <= 0:
                failure = "no progress"
                break
            written += n
    except OSError as exc:
        failure = type(exc).__name__
    try:
        os.close(fd)
    except OSError as exc:  # a deferred write error surfaces at close: still not a whole file
        failure = failure or ("close %s" % type(exc).__name__)
    if failure is None:
        return None
    # Remove ONLY the file this call created: O_EXCL proved it was ours at open, and the
    # inode comparison proves the name still points at it now.
    removed = False
    try:
        now = os.lstat(path)
        if ours is not None and (ours.st_dev, ours.st_ino) == (now.st_dev, now.st_ino):
            os.unlink(path)
            removed = True
    except OSError:
        removed = False
    return "refused: incomplete write to %s (%d of %d bytes, %s) — %s" % (
        path, written, len(data), failure,
        "the partial file was removed" if removed else "the partial file could NOT be removed: delete it before use")


def cmd_relaunch(args: argparse.Namespace) -> int:
    d = _dir(args)
    if not LL.is_run_id(args.run_id):
        print("run id has an unexpected shape", file=sys.stderr)
        return 2
    m = LL.find_launch_for_run(d, args.run_id)
    if m is None:
        print("no manifest bound to run %s — nothing exact to relaunch from (bind an orphan with `bind`, or the run predates the ledger)" % args.run_id, file=sys.stderr)
        return 4
    problem = LL.manifest_problem(m, d)
    if problem is not None:
        print("NOT EXACT: the record bound to run %s fails its integrity check (%s) — do not relaunch from it; "
              "rebuild the call from the script and args you can verify" % (args.run_id, problem), file=sys.stderr)
        return 7
    script = m.get("script") or {}
    a = m.get("args") or {}
    source = script.get("source")
    exact_script = source in ("inline", "named") or (source == "path" and script.get("unreadable") is not True)
    if not exact_script:
        print("NOT EXACT: the script of run %s was not recorded at launch (%s) — the args below are exact, the script is not"
              % (args.run_id, script.get("why") or source), file=sys.stderr)
    else:
        print("# exact recorded call for run %s (launch %s, recorded %s)" % (args.run_id, m.get("launch_id"), m.get("recorded_at")))
    if source == "named":
        print("name: %s" % m.get("name"))
    else:
        snap = LL.load_snapshot(d, m)
        if snap is not None:
            sp = LL.snapshot_path(d, m["launch_id"])
            print("scriptPath: %s   # SNAPSHOT of the bytes recorded before dispatch (sha256 %s, %d bytes)" % (sp, hashlib.sha256(snap).hexdigest(), len(snap)))
            if args.out:
                err = _write_new_file(args.out, snap)
                if err:
                    print(err, file=sys.stderr)
                    return 2
                print("snapshot copied to %s" % args.out)
            if source == "path" and script.get("path"):
                p = Path(script["path"])
                if not p.is_absolute() and m.get("cwd"):
                    p = Path(m["cwd"]) / p
                cur, why = LL.read_script_file(p)
                if cur is None:
                    print("original file %s: unreadable now (%s) — use the snapshot" % (script["path"], why))
                else:
                    print("original file %s: %s" % (script["path"], "unchanged" if hashlib.sha256(cur).hexdigest() == script.get("sha256") else "CHANGED since launch — use the snapshot"))
    if m.get("persisted_script_path"):
        print("harness copy: %s (matches snapshot: %s)" % (m["persisted_script_path"], m.get("persisted_matches_snapshot")))
    print("resumeFromRunId: %s" % args.run_id)
    if a.get("present"):
        print("args (literal JSON in the ORIGINAL key order, pass EXACTLY this):")
        print(a.get("literal"))
    else:
        print("args: ABSENT in the recorded call — do NOT pass an args field")
    code = m.get("code") or {}
    if code.get("head"):
        print("code revision at launch: %s%s" % (code["head"], " (dirty)" if code.get("dirty") else ""))
    return 0 if exact_script else 7


def cmd_check(args: argparse.Namespace) -> int:
    d = _dir(args)
    if not LL.is_run_id(args.run_id):
        print("run id has an unexpected shape", file=sys.stderr)
        return 2
    recorded = LL.find_launch_for_run(d, args.run_id)
    if recorded is None:
        print("NO-MANIFEST for run %s" % args.run_id)
        return 4
    problem = LL.manifest_problem(recorded, d)
    if problem is not None:
        print("INCONCLUSIVE: the record bound to run %s fails its integrity check (%s)" % (args.run_id, problem))
        return 6
    tool_input: Dict[str, Any] = {"resumeFromRunId": args.run_id}
    if args.script_file:
        tool_input["scriptPath"] = args.script_file
    elif args.script_text:
        data, why = LL.read_script_file(Path(args.script_text))
        if data is None:
            print("cannot read %s (%s)" % (args.script_text, why), file=sys.stderr)
            return 2
        tool_input["script"] = data.decode("utf-8", "surrogateescape")
    if args.args_file and not args.no_args:
        tool_input["args"] = json.loads(Path(args.args_file).read_text(encoding="utf-8"))
    now, _bytes = LL.build_manifest({"tool_input": tool_input, "cwd": os.getcwd()})
    cmp = LL.compare(recorded, now)
    if cmp["args"] == "inconclusive":
        print("INCONCLUSIVE: args could not be serialised on one side (run %s)" % args.run_id)
        return 6
    if cmp["counts"]["total"]:
        print("ARGS-DIFFER: run %s — %s" % (args.run_id, json.dumps(cmp["counts"])))
        for df in cmp["args_diff"]:
            print("  %-24s recorded=%s now=%s" % (df["key"], df["recorded"], df["now"]))
        if cmp["counts"].get("order"):
            print("  <key order>              the same keys and values in a different order")
        return 3
    if cmp["script"] == "differs":
        print("SCRIPT-DIFFERS (args same): run %s" % args.run_id)
        return 5
    if cmp["script"] == "inconclusive":
        print("INCONCLUSIVE: one of the script hashes is unavailable (run %s)" % args.run_id)
        return 6
    print("SAME: run %s (launch %s)" % (args.run_id, recorded.get("launch_id")))
    return 0


def cmd_bind(args: argparse.Namespace) -> int:
    d = _dir(args)
    if not LL.is_run_id(args.run_id):
        print("run id has an unexpected shape (expected wf_<hex8>[-<hex>])", file=sys.stderr)
        return 2
    m = LL.load_manifest(d, args.launch_id)
    if m is None or m.get("launch_id") != args.launch_id:
        print("no manifest %s (or its record carries another id)" % args.launch_id, file=sys.stderr)
        return 4
    LL.bind_run(d, m, args.run_id, "manual")
    print("bound %s → %s (manual)" % (args.launch_id, args.run_id))
    return 0


def cmd_orphans(args: argparse.Namespace) -> int:
    d = _dir(args)
    rows = [ln for ln in LL.iter_index(d) if ln.get("kind") == "orphan"]
    for ln in rows[-args.limit:]:
        print("%s  run=%s  session=%s  tool_use=%s  reason=%s" % (ln.get("at"), ln.get("run_id"), (ln.get("session_id") or "-")[:12], ln.get("tool_use_id") or "-", ln.get("reason")))
    print("orphans: %d" % len(rows))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    d = _dir(args)
    idx = LL.iter_index(d)
    launches = [ln for ln in idx if ln.get("kind") == "launch"]
    guard: Dict[str, int] = {}
    methods: Dict[str, int] = {}
    bound = 0
    for ln in launches:
        m = LL.load_manifest(d, ln["launch_id"]) or {}
        g = (m.get("guard") or {}).get("result", "?")
        guard[g] = guard.get(g, 0) + 1
        if m.get("run_id"):
            bound += 1
            bm = m.get("bind_method") or "?"
            methods[bm] = methods.get(bm, 0) + 1
    orphans = sum(1 for ln in idx if ln.get("kind") == "orphan")
    print("launches=%d bound=%d unbound=%d orphans=%d" % (len(launches), bound, len(launches) - bound, orphans))
    print("guard results: %s" % json.dumps(guard, sort_keys=True))
    print("bind methods:  %s" % json.dumps(methods, sort_keys=True))
    print("ledger: %s" % d)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project-dir", default=None, help="runtime state dir root to use instead of the resolver (tests / other projects)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--limit", type=int, default=20); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("ident"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("relaunch"); p.add_argument("run_id"); p.add_argument("--out", default=None); p.set_defaults(fn=cmd_relaunch)
    p = sub.add_parser("check"); p.add_argument("--run", dest="run_id", required=True)
    p.add_argument("--script-file", default=None); p.add_argument("--script-text", default=None)
    p.add_argument("--args-file", default=None); p.add_argument("--no-args", action="store_true"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("bind"); p.add_argument("launch_id"); p.add_argument("run_id"); p.set_defaults(fn=cmd_bind)
    p = sub.add_parser("orphans"); p.add_argument("--limit", type=int, default=50); p.set_defaults(fn=cmd_orphans)
    p = sub.add_parser("report"); p.set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
