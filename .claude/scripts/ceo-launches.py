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
                                                integrity check (snapshot hash, args canonical/hash) or its
                                                snapshot cannot be read back unchanged. --out FILE publishes a NEW file:
                                                an exclusive temporary inside a private directory created in
                                                FILE's directory, written, fsync'ed, then linked to FILE (never
                                                replaces; the cleanup removes, by name, only the two names this call
                                                created — the temporary only once this call has recorded that its
                                                exclusive create succeeded) —
                                                rc 2 when FILE is refused or the copy fails, and for a named workflow
                                                (no recorded bytes to copy); a script not recorded at launch stays rc 7.
                                                After rc 2 do not use a file at FILE: a refusal made after the link
                                                that says it cannot tell whether FILE holds the copy, or that FILE is
                                                not the temporary this call wrote, can leave at FILE what the link
                                                published; every other refusal leaves nothing this call published there
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
import errno
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


# ``relaunch --out`` acts on open directory descriptors (openat / mkdirat / linkat /
# unlinkat / fstatat): the private directory is created INSIDE the destination's
# directory, so the temporary and the destination are on the same filesystem and
# ``link`` can join them.
_DIR_FD_OK = ({os.open, os.link, os.unlink, os.stat, os.mkdir, os.rmdir} <= os.supports_dir_fd
              and {os.link, os.stat} <= os.supports_follow_symlinks)
# What ``--out`` creates, named so a leftover is recognisable: the private directory
# ``<prefix><16 hex>`` in the destination's directory, and the temporary inside it.
_TMP_PREFIX = ".ceo-launches-out-"
_TMP_NAME = "snapshot.part"
# The destination's directory, and the private directory created in it, are only searched through,
# never listed: both are opened for search only where Python exposes such a flag (O_PATH on
# Linux, O_SEARCH on macOS), so a directory the user can write and search but not read (a drop
# directory, mode 0300; a private directory whose owner read bit the umask cleared) is accepted;
# elsewhere they are opened O_RDONLY and such a directory is refused.
_DEST_DIR_FLAGS = ((getattr(os, "O_PATH", 0) or getattr(os, "O_SEARCH", 0) or os.O_RDONLY)
                   | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0))
_TMP_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
# What ``link`` answers on a filesystem without hard links (FAT/exFAT volumes, some network shares).
_NO_HARDLINK_ERRNOS = frozenset(getattr(errno, n) for n in ("EPERM", "ENOTSUP", "EOPNOTSUPP", "EXDEV", "EMLINK")
                                if hasattr(errno, n))


def _why(exc: BaseException) -> str:
    """The exception's type and, when it carries one, its errno name (``PermissionError EACCES``)."""
    code = getattr(exc, "errno", None)
    name = errno.errorcode.get(code) if isinstance(code, int) else None
    return "%s %s" % (type(exc).__name__, name) if name else type(exc).__name__


def _write_new_file(path: str, data: bytes) -> Optional[str]:
    """Publish ``data`` as a NEW file at ``path``: every byte under that name, or none of them
    under it — while the machine stays up (after a power loss nothing is claimed: no directory
    is fsync'ed, and ``fsync`` on macOS does not flush the drive's cache) and while, during the
    call, nothing else writes the destination's directory as this call opened it, changes what a
    directory on the path to ``path`` resolves to (a rename, a re-pointed symlink, a mount), or
    writes what this call creates (the limits declared in docs/workflow-recovery.md, "relaunch
    --out (declared)"; see the tampering limit below). Returns ``None`` only once the
    destination is, by (device, inode), the
    temporary this call wrote; an error text otherwise — one that says it cannot tell, or that
    the destination is not that temporary, can come with what ``link`` published at the
    destination.

    Shape (PLAN-190-FOLLOWUP; Owner decision 2026-09-18, private directory added after the
    S357 rail round 2): the bytes go to an exclusive temporary (``O_CREAT|O_EXCL|O_NOFOLLOW``,
    mode 0600 requested) inside a directory this call creates for them, mode 0700 requested, in
    the destination's directory — the same filesystem by construction. "Private" names that
    directory's role, not an access guarantee: the umask applies to both requested modes, and
    access the filesystem grants beyond mode bits (inheritable ACL entries on macOS) reaches the
    directory, the temporary and the published file for whoever those entries name. The bytes
    are written to the last byte and ``fsync``'ed, and only then receive the destination name
    through ``link``, which never replaces an existing entry: a file, symlink or directory
    already there is ``EEXIST``, a named refusal. Partial bytes are therefore never an entry of
    the destination's directory; they sit only inside the private directory: a destination that
    the filesystem treats as the same name as the private directory (by case, by folding) can
    only name that directory, and ``link`` then refuses. After ``link``, success or error, what
    the destination names is compared by (device, inode) with the identity ``fstat`` took from
    the temporary's descriptor; only that identity is announced as the copy (on a filesystem
    that reported one file's identity differently through the destination name than through
    that descriptor, every copy would be refused — no such filesystem was measured). The
    ``finally`` removes, by name, the two names this call created:
    the temporary (only once this call has recorded that its exclusive create succeeded — an
    interruption between that create and the record leaves it, with the directory), then the
    private directory. The
    destination name itself is never passed to unlink, rmdir, rename or replace. Removal by
    name trusts the destination's directory the way the ledger's is trusted: someone who can
    write it can put another EMPTY directory under the private directory's name while this
    runs, and that one is then removed (declared in docs/workflow-recovery.md). A copy
    truncated here would be exactly the material the recovery rite passes back as
    ``scriptPath`` (PLAN-190 W1.1)."""
    parent, name = os.path.split(path)
    if not name or name in (".", ".."):
        return "refused: %s does not name a file (relaunch --out needs a file path)" % path
    if not _DIR_FD_OK:
        return "refused: cannot create %s: this platform lacks the directory-relative calls relaunch --out needs" % path
    try:
        dfd = os.open(parent or ".", _DEST_DIR_FLAGS)
    except (OSError, ValueError) as exc:
        return "refused: cannot open the directory of %s (%s)" % (path, _why(exc))
    try:
        return _publish_new_file(dfd, path, name, data)
    finally:
        try:
            os.close(dfd)
        except OSError:
            pass


def _publish_new_file(dfd: int, path: str, name: str, data: bytes) -> Optional[str]:
    # Fast path only: a name that exists now is refused before anything is created.
    # The refusal that holds under a race is the one ``link`` itself returns below.
    try:
        os.stat(name, dir_fd=dfd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        return "refused: cannot inspect %s (%s)" % (path, _why(exc))
    else:
        return "refused: %s already exists (relaunch --out never overwrites)" % path
    priv = "%s%s" % (_TMP_PREFIX, secrets.token_hex(8))
    priv_shown = os.path.join(os.path.dirname(path), priv)
    try:
        os.mkdir(priv, 0o700, dir_fd=dfd)
    except (OSError, ValueError) as exc:
        return "refused: cannot create a private directory next to %s (%s) — nothing was published" % (path, _why(exc))
    pfd: Optional[int] = None
    tmp_made = False  # True only once THIS call's exclusive create succeeded: an entry it did not create is never removed
    tmp_id: Optional[Tuple[int, int]] = None
    written = 0
    failure: Optional[str] = None
    refusal: Optional[str] = None
    try:
        try:
            # Opened like the destination's directory (search only where Python exposes the flag).
            # Where O_PATH or O_SEARCH exists, only the owner's write and search bits of the private
            # directory decide: O_PATH (Linux) checks no permission on the directory itself, so a
            # missing bit refuses at the create below; O_SEARCH (macOS) checks search here. Where
            # the flag falls back to O_RDONLY, this open also needs the owner's read bit.
            pfd = os.open(priv, _DEST_DIR_FLAGS | getattr(os, "O_NOFOLLOW", 0), dir_fd=dfd)
        except (OSError, ValueError) as exc:
            failure = "opening the private directory: %s" % _why(exc)
        else:
            try:
                fd = os.open(_TMP_NAME, _TMP_FLAGS, 0o600, dir_fd=pfd)
            except (OSError, ValueError) as exc:
                failure = "creating the temporary: %s" % _why(exc)
        if failure is None:
            tmp_made = True
            try:
                # ``os.write`` may write FEWER bytes than asked: loop until every byte is down.
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
                if failure is None:
                    try:
                        os.fsync(fd)
                    except OSError as exc:
                        failure = "fsync %s" % _why(exc)
                if failure is None:
                    try:  # the temporary's identity is what decides, after the link, whether FILE is the copy
                        tst = os.fstat(fd)
                        tmp_id = (tst.st_dev, tst.st_ino)
                    except OSError as exc:
                        failure = "fstat %s" % _why(exc)
            except OSError as exc:
                failure = failure or _why(exc)
            finally:
                try:
                    os.close(fd)
                except OSError as exc:  # a deferred write error surfaces at close: still not a whole file
                    failure = failure or ("close %s" % _why(exc))
            if failure is None:
                try:
                    os.link(_TMP_NAME, name, src_dir_fd=pfd, dst_dir_fd=dfd, follow_symlinks=False)
                except (OSError, NotImplementedError) as exc:
                    # Decided by identity (device, inode), never by spelling. Whatever ``link``
                    # answered, the temporary itself at the destination name means it created the
                    # name (a retransmitted LINK on NFS answers EEXIST): the whole copy is published.
                    try:
                        at = _entry_id(dfd, name)
                    except (OSError, ValueError) as sexc:
                        refusal = "unknown"
                        failure = "link %s, then reading what that name holds: %s" % (_why(exc), _why(sexc))
                    else:
                        if at != tmp_id:
                            if isinstance(exc, FileExistsError):
                                refusal = "alias" if at is not None and at == _fd_id(pfd) else "taken"
                            else:
                                failure = "link %s" % _why(exc)
                                if getattr(exc, "errno", None) in _NO_HARDLINK_ERRNOS:
                                    failure += ": this filesystem may not support hard links, which " \
                                               "relaunch --out needs — choose a FILE on one that does"
                else:
                    # ``link`` publishes whatever the temporary's NAME held at that instant. The same
                    # identity test as above: FILE is announced as the copy only when it is, by
                    # (device, inode), the object ``fstat`` identified through the descriptor the
                    # bytes were written and fsync'ed through — never by the temporary's name.
                    try:
                        at = _entry_id(dfd, name)
                    except (OSError, ValueError) as sexc:
                        refusal = "unknown"
                        failure = "link succeeded, then reading what that name holds: %s" % _why(sexc)
                    else:
                        if at != tmp_id:
                            refusal = "foreign"
    finally:
        left = _remove_created(dfd, priv, pfd, tmp_made)
    if left is None:
        if refusal == "foreign":  # the entry under the temporary's name may not be the object this call wrote
            fate = "the private directory and what was under the temporary's name were removed"
        else:
            fate = "the temporary and its private directory were removed" if tmp_made else "its private directory was removed"
    else:
        fate = "the private directory %s could NOT be removed (%s): delete it — nothing in it is a verified copy" % (
            priv_shown, left)
    if refusal == "alias":
        return "refused: on this filesystem %s is the same name as the private directory relaunch --out created " \
               "for the copy (%s: the two spellings are equivalent here, for example by case) — nothing was " \
               "published at %s; %s" % (path, priv_shown, path, fate)
    if refusal == "taken":
        return "refused: %s already exists — the name was taken while the copy was being written; " \
               "relaunch --out never overwrites, nothing was replaced; %s" % (path, fate)
    if refusal == "unknown":
        return "refused: cannot tell whether %s holds the copy (%s) — do not use a file at %s; %s" % (
            path, failure, path, fate)
    if refusal == "foreign":
        return "refused: after the link, %s is not the temporary this call wrote (compared by device and inode) " \
               "— do not use a file at %s, which is left as it is; %s" % (path, path, fate)
    if failure is not None and failure.startswith(("opening ", "creating ", "link ")):
        return "refused: cannot create %s (%s) — nothing was published at %s; %s" % (path, failure, path, fate)
    if failure is not None:
        return "refused: incomplete write for %s (%d of %d bytes, %s) — nothing was published at %s; %s" % (
            path, written, len(data), failure, path, fate)
    if left is not None:
        print("note: %s holds the whole copy; the private directory %s could not be removed (%s) and may hold a "
              "second name of the copy — delete that directory" % (path, priv_shown, left), file=sys.stderr)
    return None


def _entry_id(dfd: int, name: str) -> Optional[Tuple[int, int]]:
    """(device, inode) of the entry ``name`` in ``dfd``, never following a symlink; ``None`` when
    there is no such entry. Any other error propagates: an entry that cannot be read is not an
    absent one. Identity, never spelling: the filesystem's name rules decide."""
    try:
        st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return (st.st_dev, st.st_ino)


def _fd_id(fd: int) -> Optional[Tuple[int, int]]:
    """(device, inode) of the object open as ``fd``; ``None`` if it cannot be read."""
    try:
        st = os.fstat(fd)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def _remove_created(dfd: int, priv: str, pfd: Optional[int], tmp_made: bool) -> Optional[str]:
    """Remove, by name, the two names this call created: the temporary inside the private
    directory, only when this call's exclusive create of it succeeded, then the private
    directory. No other name is removed. A removal by name is not the removal of an object:
    someone who can write the destination's directory can put another EMPTY directory under
    the private directory's name meanwhile, and ``rmdir`` then removes that one (declared in
    docs/workflow-recovery.md). ``None`` once both names are gone."""
    problem: Optional[str] = None
    if pfd is not None:
        if tmp_made:
            try:
                os.unlink(_TMP_NAME, dir_fd=pfd)
            except FileNotFoundError:
                pass
            except OSError as exc:
                problem = _why(exc)
        try:
            os.close(pfd)
        except OSError:
            pass
    try:
        os.rmdir(priv, dir_fd=dfd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        problem = problem or _why(exc)
    return problem


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
    snap: Optional[bytes] = None
    if source != "named":
        snap = LL.load_snapshot(d, m)
        if exact_script and (snap is None or hashlib.sha256(snap).hexdigest() != script.get("sha256")):
            # The integrity check above verified ITS read; these are the bytes printed and copied,
            # so they are held to the same recorded hash — else the same verdict (rc 7, nothing exact).
            print("NOT EXACT: the script snapshot of run %s %s after its integrity check — do not relaunch from it; "
                  "rebuild the call from the script and args you can verify"
                  % (args.run_id, "could not be read back" if snap is None else "changed when read back"), file=sys.stderr)
            return 7
    if not exact_script:
        print("NOT EXACT: the script of run %s was not recorded at launch (%s) — the args below are exact, the script is not"
              % (args.run_id, script.get("why") or source), file=sys.stderr)
    else:
        print("# exact recorded call for run %s (launch %s, recorded %s)" % (args.run_id, m.get("launch_id"), m.get("recorded_at")))
    if source == "named":
        print("name: %s" % m.get("name"))
    else:
        if snap is not None:
            sp = LL.snapshot_path(d, m["launch_id"])
            print("scriptPath: %s   # SNAPSHOT of the bytes recorded before dispatch (sha256 %s, %d bytes)" % (sp, hashlib.sha256(snap).hexdigest(), len(snap)))
            if args.out is not None:  # an explicit ``--out ""`` is a request too — refused, never ignored
                err = _write_new_file(args.out, snap)
                if err:
                    print(err, file=sys.stderr)
                    return 2 if exact_script else 7  # a script not recorded at launch stays rc 7
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
    rc = 0 if exact_script else 7
    if args.out is not None and snap is None:
        # An --out that creates no file never exits 0 and is never silent.
        print("refused: --out has nothing to copy for run %s: %s — no file was created at %s" % (
            args.run_id,
            "it was launched by name (the harness resolves the script by that name; no bytes were recorded)"
            if source == "named" else "its script was not recorded at launch",
            args.out), file=sys.stderr)
        return rc or 2
    return rc


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
