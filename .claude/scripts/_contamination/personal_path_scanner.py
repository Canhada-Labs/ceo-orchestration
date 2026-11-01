"""Rule 2 personal-path implementations bound into the legacy facade."""
from __future__ import annotations

import errno
import hashlib
import os
import re
import stat
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


def in_personal_path_scope(rel_path: str) -> bool:
    """True for a repo-relative POSIX path inside the rule's two trees.

    A tracked entry that IS a scope root, or an ancestor of one, counts.
    Git stores no directories, so such an entry can only be a SYMLINK:
    `docs -> /Users/<owner>/repo` replaces the whole tree with a link,
    and the plain `startswith` answered False for it — the scope test
    itself was a way out of the scope (pair-rail round 1, P1, both
    lanes). MEASURED: no such entry exists on this tree, so the
    widening moves no row; it removes a shape.
    """
    if rel_path.startswith(_PERSONAL_PATH_SCOPE):
        return True
    prefix = rel_path + "/"
    return any(scope.startswith(prefix) for scope in _PERSONAL_PATH_SCOPE)


def _personal_path_owner_segments(line: str) -> List[str]:
    """Lowercased home-directory owner segments named on ``line``."""
    segments = [m.group(1) for m in _PERSONAL_PATH_HOME_RE.finditer(line)]
    segments += [m.group(1) for m in _PERSONAL_PATH_SLUG_RE.finditer(line)]
    return [s.lower() for s in segments]


def _personal_path_names_a_person(line: str) -> bool:
    """One reading of ``line``: does it name a non-placeholder home owner?"""
    if not _PERSONAL_PATH_LITERAL_RE.search(line):
        return False
    return any(
        seg not in _PERSONAL_PATH_PLACEHOLDERS
        for seg in _personal_path_owner_segments(line)
    )


def line_is_personal_path_hit(line: str) -> bool:
    """True when ``line`` names a home directory that is not a placeholder.

    TWO readings, because one of them is not enough. An undecodable byte in
    the line is UNPARSEABLE INPUT, and the decoder's U+FFFD SPLITS a literal
    (`/Us<0xFF>ers/`, which the fast path then rejects) and can make an owner
    segment unrecognisable. Fail CLOSED per the CLAUDE.md §4 rule for security
    matchers — the reading with the replacement removed is what the author's
    bytes could have meant, so a hit in EITHER reading is a hit.

    (An earlier version of this paragraph said U+FFFD TRUNCATES an owner
    segment to a placeholder prefix, with `/Users/dev<0xFF>name` reading as
    owner `dev`. That was true of an older owner class and is not true of
    this one: U+FFFD is not in the shared delimiter set, so the capture is
    the whole `dev<U+FFFD>name` and the line is a HIT in the FIRST reading.
    Measured on this module — text lane, round 23. The three clauses below
    are unchanged; only the example was wrong.)

    Two readings were still not enough (pair-rail land round 1, P1): the
    removal can RECONSTRUCT a placeholder as easily as the truncation can
    produce one — `/Users/dev<0xFF>user/work` reads as owner `dev` with
    the marker in place and as `devuser` with it removed, and BOTH are on
    the placeholder list, so a real owner hid behind one byte. Enumerating
    readings cannot close that: whatever the pair of readings answers, the
    matcher does not KNOW what the bytes said.

    So the third clause is the CLAUDE.md §4 rule itself, stated once: an
    unreadable byte on a line that names a home path in EITHER reading is
    unparseable input inside a security matcher, and unparseable input is
    a HIT. A human then looks at the bytes; the recoverable failure is one
    allowlist row with a written reason.

    Monotone: each clause can only ADD findings. On the tree this
    shipped from all three agreed — the CENSUS above counts the hit
    files, and NO in-scope file carries an undecodable byte on a
    home-path line at all.
    """
    if _personal_path_names_a_person(line):
        return True
    if not _PERSONAL_PATH_UNDECODABLE_RE.search(line):
        return False
    stripped = _PERSONAL_PATH_UNDECODABLE_RE.sub("", line)
    if _personal_path_names_a_person(stripped):
        return True
    return bool(_PERSONAL_PATH_LITERAL_RE.search(line)
                or _PERSONAL_PATH_LITERAL_RE.search(stripped))


def personal_path_hit_lines(
    text: str, deadline: Optional[float] = None,
) -> Tuple[int, ...]:
    """1-based line numbers of every hit line in ``text``.

    Returns NUMBERS, never content: the caller — including a CLI whose output
    lands in a public CI log — is left with nothing quotable.

    `split("\\n")`, NOT `splitlines()`: the report is `file:line`, and a human
    resolves that with `sed -n '<N>p'` or `grep -n`, both of which count
    `\\n`. `splitlines()` ALSO breaks on `\\v`, `\\f`, `\\x1c`-`\\x1e`, U+2028
    and U+2029 — one vertical tab in a frozen transcript would shift every
    line number after it, and a finding that points at the wrong line is a
    finding a reviewer cannot check. NFKC therefore runs PER LINE, after the
    split, so normalisation cannot move the boundaries either.

    ``deadline`` is a `time.monotonic()` value, not a duration, so the
    budget belongs to the CALLER that knows what it is scanning. When it
    passes, the scan REFUSES the file (`PersonalPathUnreadable`, which
    the CLI renders as rc 2) instead of returning the lines it had found:
    a partial answer from a security matcher is not a clean file.

    It is consulted AFTER every line, and the claim is exactly that: it
    bounds the file ACROSS its lines. It does NOT interrupt work already
    running inside one line, and `unicodedata.normalize` is work that can
    itself be super-linear -- 140 000 combining marks followed by 140 000
    more took 38.186 s in one call (mechanism lane, round 22). After such
    a line the deadline fires, so the outcome is a NAMED refusal instead
    of a silent green; the seconds spent on that line are not recovered,
    and the honest boundary for them is the outer CI timeout.
    """
    hits: List[int] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if line_is_personal_path_hit(unicodedata.normalize("NFKC", line)):
            hits.append(lineno)
        # AFTER the line, and after EVERY line -- both halves are the
        # cure, and each was a defect on its own. Checking every 512th
        # line left a document of ONE line unchecked. Checking at the TOP
        # of the body left it unchecked too, for a subtler reason: the
        # single check then runs before any work has been done, and the
        # loop ends without another one. Measured after that cure:
        # 140 000 U+0315 followed by 140 000 U+0300 took 72.2 s and
        # returned 0 on a 30 s budget. After the line, there is something
        # to detect; before it, there is not.
        if deadline is not None and time.monotonic() > deadline:
            raise PersonalPathUnreadable(
                "matching did not finish within the per-file deadline of "
                "%.0f s (stopped after line %d); the file is REFUSED "
                "rather than reported clean"
                % (_PERSONAL_PATH_FILE_BUDGET_S, lineno))
    return tuple(hits)






def _personal_path_read_nofollow(path: Path) -> Optional[PersonalPathBlob]:
    """Read an entry git called a REGULAR FILE, refusing to follow a link.

    `is_symlink()` then `read_bytes()` are two answers about two moments:
    replace the file with a link between them and the read follows it
    while the recorded classification still says "not a link" — enough
    to scan a link's target as though it were file content, and (while
    the rule waiver still existed) enough to earn it (pair-rail round
    1, P1).
    `O_NOFOLLOW` collapses both into one syscall: either it opens the
    inode the name pointed at, or it refuses because that name is a link.

    A refusal is not an error here, it is a FINDING: git enumerated this
    entry as a regular file and the filesystem disagrees, so the link is
    scanned as a link — its TARGET STRING is the content matched, never
    followed — and `is_symlink=True` travels with the blob. The target
    may well be clean; what is closed is the path where a link was read
    as the file it points at.

    A non-regular inode does NOT yield None. A directory raises
    `PersonalPathUnreadable` (errno EISDIR below), and so does a FIFO, a
    socket or a device at the `S_ISREG` test, because git enumerated a
    blob here and the disk holds something that is not one: an entry
    this rule cannot read is an UNVERIFIED entry, not a clean one
    (pair-rail round 4, P1 -- returning None here was a silent skip, and
    this docstring went on saying so until round 17 read it). `None` is
    for an entry that is simply ABSENT (ENOENT / ENOTDIR). The open
    carries
    `O_NONBLOCK` so that classification can happen at all -- without it
    a FIFO left in place of a tracked file blocks the open until a
    writer connects and the scan never reaches the fstat below
    (pair-rail round 3, P2).
    """
    try:
        fd = os.open(str(path),
                     os.O_RDONLY | _PERSONAL_PATH_O_NOFOLLOW
                     | _PERSONAL_PATH_O_NONBLOCK)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, getattr(errno, "EMLINK", None)):
            return PersonalPathBlob(
                raw=os.fsencode(os.readlink(path)), is_symlink=True)
        if exc.errno in (errno.ENOENT, errno.ENOTDIR):
            return None
        if exc.errno == errno.EISDIR:
            # PRESENT and not readable as a blob. Returning None here
            # made a tracked path replaced by a DIRECTORY a silent
            # skip (pair-rail round 4, P1).
            raise PersonalPathUnreadable(
                "a tracked entry is a DIRECTORY on disk; it exists and "
                "holds no blob, so the scan has no verdict for it")
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            # A FIFO, a socket, a device: PRESENT, and not a blob.
            # `O_NONBLOCK` (round 3) stopped the hang; returning None
            # here then turned the hang into a CLEAN UNREAD SCAN, which
            # is worse (pair-rail round 4, P1). Fail-closed: the mode is
            # named, the path is not.
            raise PersonalPathUnreadable(
                "a tracked entry is not a regular file on disk "
                "(st_mode 0o%o); it exists and holds no blob, so the "
                "scan has no verdict for it"
                % stat.S_IFMT(os.fstat(fd).st_mode))
        chunks = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            chunks.append(block)
        return PersonalPathBlob(raw=b"".join(chunks), is_symlink=False)
    finally:
        os.close(fd)


def _personal_path_index_modes(repo_root: Path) -> Dict[str, str]:
    """`{repo-relative path: git index mode}` for every tracked entry.

    The rule asks git — not the filesystem — whether an entry is a link
    (see `_PERSONAL_PATH_LINK_MODE`). Failing to get that answer is not a
    reason to guess: a scan that cannot classify its inputs is an
    unverified scan, which this rule already calls fatal everywhere else.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=str(repo_root), capture_output=True, check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        raise PersonalPathUnreadable(
            "cannot read the git index (git unavailable or timed out); "
            "the scan cannot tell a symlink from a file") from None
    if proc.returncode != 0:
        raise PersonalPathUnreadable(
            "cannot read the git index (git ls-files -s exited %d); the "
            "scan cannot tell a symlink from a file" % proc.returncode)
    modes: Dict[str, str] = {}
    for entry in proc.stdout.decode("utf-8", errors="replace").split("\0"):
        if not entry:
            continue
        head, _, name = entry.partition("\t")
        if name:
            modes[name] = head.split(" ", 1)[0]
    return modes


#: The line number a PATH hit is reported under. A hit in the NAME has no
#: line, and `file:0` is the shape every reader of `grep -n` already knows
#: means "not a line of content". The report prints a legend for it.
_PERSONAL_PATH_NAME_LINE = 0


def _personal_path_undecodable_in_scope(rel: str) -> bool:
    """True when an undecodable path is, or might be, this rule's subject.

    The first cut raised on ANY undecodable tracked path, so a legal
    byte-name under `assets/` turned the whole gate rc 2 for a rule that
    does not scan `assets/` at all (pair-rail round 2, P2). The fail-closed
    rule is about a matcher's INPUT, and out of scope it was never input.

    UNDECIDABLE counts as in scope, and the test for it is exact rather
    than a segment count: `in_personal_path_scope` is a `startswith` over
    `_PERSONAL_PATH_SCOPE`, so the verdict is fully determined by the
    characters BEFORE the first marker unless one of the prefixes is still
    alive at that point -- i.e. unless the marker falls inside a prefix and
    everything decoded so far matches it. `do<marker>s/note.md` is fatal
    (`docs/` is still alive at index 2); `assets/img<marker>.png` is not
    (no prefix survives its first character).
    """
    match = _PERSONAL_PATH_UNDECODABLE_RE.search(rel)
    if match is None:
        return False
    if in_personal_path_scope(rel):
        return True
    head = rel[:match.start()]
    return any(len(head) < len(prefix) and prefix.startswith(head)
               for prefix in _PERSONAL_PATH_SCOPE)


def _personal_path_assert_enumerable(repo_root: Path) -> None:
    """Fatal unless git really did enumerate ZERO tracked files.

    `FileWalker._iter_git_tracked` returns an EMPTY iterator when `git` is
    missing, times out, or exits non-zero (`_lib/file_walker.py:80-93`) --
    the same shape a genuinely empty repository has. A gate that prints
    "no contamination" because it looked at nothing is a false green, and
    an enumeration that failed is not a verdict (pair-rail round 1, P2).

    This is a GATE, not a hook: the CLAUDE.md §4 fail-open applies to hooks
    that must not block a user session. Nothing here blocks a session, and
    the module already answers rc 2 for an in-scope file it cannot read --
    so an enumeration it cannot trust is rc 2 too, by the same rule.

    Called ONLY when the walk yielded nothing, so the ordinary run pays for
    no second enumeration. The message names no path.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(repo_root), capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise PersonalPathUnreadable(
            "cannot enumerate tracked files (git unavailable or timed "
            "out); the scan looked at nothing and has no verdict") from None
    if proc.returncode != 0:
        raise PersonalPathUnreadable(
            "cannot enumerate tracked files (git ls-files exited %d); the "
            "scan looked at nothing and has no verdict" % proc.returncode)
    listed = [name for name in proc.stdout.split(b"\0") if name]
    if listed:
        # The RETRY worked and the repository is NOT empty, so the walk
        # that yielded nothing was the thing that failed. Checking only
        # the return code here turned a transient first failure into a
        # clean verdict over zero files (pair-rail round 1, P1, both
        # lanes) — the exact false green this assertion exists to stop.
        raise PersonalPathUnreadable(
            "the walk yielded NOTHING while git lists %d tracked file(s); "
            "the enumeration failed and the scan has no verdict"
            % len(listed))


def scan_personal_paths(repo_root: Path) -> PersonalPathScan:
    """Every in-scope tracked file carrying a personal path — ALL of them.

    UNIFORM: every in-scope tracked path is read and matched the same
    way. No basename, no suffix and no directory decides that a file is
    not looked at, because three versions of this pack shipped such a
    skip and the pair-rail found each one (`.asc` by suffix, sentinels by
    basename, `OWNER-*.sh` by basename — the last of those dropped v3 at
    the land). This function decides NO waiver at all: it reports what
    it found, and the only thing that may forgive a finding is a
    content-pinned row, applied later by `personal_path_verdict`.

    Walks tracked files with NO path allowlist at all: the term rule's
    allowlist is what hid this class, and consulting it here would
    re-hide it.

    The PATH is a subject, not just an address (pair-rail land round 2,
    G3). `docs/-Users-<name>-project/note.md` with a clean body used to
    pass, though the rule's own predicate answers True on that string --
    the slug form in a directory name is exactly what the harness writes,
    and it is a RENAME, not a waiver.
    MEASURED before choosing it (CENSUS at the top of this block):
    ZERO in-scope tracked paths hit on their own name today, so the
    new subject adds no row.

    **A waiver waives the BODY, never the NAME** (pair-rail round 1, P1).
    The v2 cut tested exemption BEFORE the path, so an exempt file under
    a contaminated directory -- `docs/-Users-<name>-x/wave-approved.md`
    -- was `continue`d and its own path never examined. Ordering cured
    the symptom; v4 removed the shape. Nothing is skipped at all now,
    so there is no ordering left to get wrong: the name is judged and
    the body is read, always, and only a row may forgive BODY lines.
    `personal_path_verdict` refuses to consider any waiver for a hit
    carrying line 0, and the allowlist parser separately refuses a row
    naming a home directory -- two independent reasons a name cannot be
    waived, neither of them a property of one parser.

    Raises ``PersonalPathUnreadable`` when a file that exists cannot be
    read, and when a tracked path is not valid UTF-8: `FileWalker` decodes
    `git ls-files -z` with `errors="replace"`, so such an entry arrives as
    a name that does not exist, `is_file()` answers False and the file was
    SKIPPED IN SILENCE (pair-rail land round 2, G2). A path the scan cannot
    address is unparseable input, and unparseable input in a security
    matcher is fatal (CLAUDE.md §4). MEASURED (CENSUS above): ZERO
    tracked paths are undecodable in scope.
    The message names NO path -- a mangled name is the one string the
    redactor cannot reason about, so nothing about it is echoed.

    Also raises it when the walk yielded NOTHING and git cannot confirm the
    tree is empty, and when the set of paths the walk actually saw does
    not COVER the index -- see `_personal_path_assert_enumerable`. A
    PARTIAL walk is a false green with a smaller blast radius than an
    empty one, and the index is already in hand, so it costs nothing to
    refuse it (pair-rail round 2: the empty-only assertion was the weaker
    half of the question it was asking; round 3: so was counting, because
    a walk that yields one path twice has the right COUNT and the wrong
    coverage).

    And when an in-scope entry carries an index mode this rule cannot
    turn into bytes (`_PERSONAL_PATH_BLOB_MODES`): a gitlink opened as a
    directory, yielded nothing, and still counted as a file the walk had
    seen (pair-rail round 3, P1). Out-of-scope entries are unaffected --
    the scope test comes first, so a submodule elsewhere in the tree is
    not this rule's business.
    """
    walker = FileWalker(repo_root=repo_root, mode="git")
    modes = _personal_path_index_modes(walker.repo_root)
    hits: List[PersonalPathHit] = []
    # IDENTITIES, not a count. `seen == len(modes)` was satisfied by a
    # walk that yielded one path twice while another tracked file was
    # never read, and reported clean over it (pair-rail round 3, P1).
    # A set answers the question the assertion was always asking:
    # WHICH tracked files did this scan actually look at?
    seen_rels = set()
    for path in walker.iter_files():
        try:
            rel = path.relative_to(walker.repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        seen_rels.add(rel)
        if _personal_path_undecodable_in_scope(rel):
            raise PersonalPathUnreadable(
                "a tracked path is not valid UTF-8; the scan cannot "
                "address it (rename it, then re-run)")
        if not in_personal_path_scope(rel):
            continue
        # An index mode this rule cannot turn into bytes is a REFUSAL,
        # not a skip: the 160000 gitlink opened as a directory, gave
        # `None`, and still counted as seen (pair-rail round 3, P1).
        # The message names the MODE and a masked path -- a path can
        # itself be the leak this rule exists to keep out of a log.
        # A MISSING mode is not a pass. `modes` and the walk are two
        # enumerations of the same index taken moments apart, so an
        # in-scope path the snapshot does not know is an inconsistent
        # scan -- and `modes.get(rel) is None` skipped the whole check
        # (pair-rail round 4, P2).
        entry_mode = modes.get(rel)
        if entry_mode is None:
            raise PersonalPathUnreadable(
                "%s: in scope and absent from the index snapshot taken "
                "by this same call; the scan is inconsistent and has "
                "no verdict" % _personal_path_mask_rel(rel))
        if entry_mode not in _PERSONAL_PATH_BLOB_MODES:
            raise PersonalPathUnreadable(
                "%s: index mode %s is not a blob this rule can read; "
                "the scan has no verdict for it"
                % (_personal_path_mask_rel(rel), entry_mode))
        lines: Tuple[int, ...] = ()
        # The NAME is judged, and nothing waives a name.
        if line_is_personal_path_hit(unicodedata.normalize("NFKC", rel)):
            lines += (_PERSONAL_PATH_NAME_LINE,)
        digest: Optional[str] = None
        digest_lf: Optional[str] = None
        blob = _personal_path_blob(
            path, rel,
            index_is_link=modes.get(rel) == _PERSONAL_PATH_LINK_MODE)
        if blob is not None:
            # A NUL is not text, and this matcher only reads text.
            # A UTF-16 or UTF-32 document decodes HERE, with
            # `errors="replace"`, into ASCII interleaved with NULs:
            # every one of those bytes is individually VALID UTF-8, so
            # THE LINE THAT CARRIES THE HOME PATH produces no U+FFFD,
            # the second reading of `line_is_personal_path_hit` never
            # fires for it, and the NULs split every literal the fast
            # path looks for. (The BOM does decode to two U+FFFD, on the
            # FIRST line -- text lane, round 19. It is a different line,
            # and the second reading is per line, so it never reaches
            # the one being hidden.) Reproduced
            # (mechanism lane, round 18): the same two lines committed
            # under `docs/` twice, once as UTF-8 and once as UTF-16,
            # gave ONE hit -- the UTF-16 copy read CLEAN.
            #
            # Unparseable input to a security matcher is fail-CLOSED
            # (CLAUDE.md section 4), so this REFUSES rather than scan a
            # decoding it cannot trust. MEASURED before shipping by the
            # pack instrument `measure-nul-census.py`, which prints both
            # numbers and is runnable from the repository root: of the
            # in-scope tracked files, ZERO carry a NUL -- the refusal
            # moves no file, it removes a shape. (The instrument counts
            # with a git pathspec, so its total is its own derivation
            # rather than a correction of the CENSUS table above.) The
            # message names the MASKED path and the remedy.
            if b"\x00" in blob.raw:
                raise PersonalPathUnreadable(
                    "%s: the bytes carry a NUL, so they are not the "
                    "UTF-8 text this rule reads (a UTF-16/UTF-32 or "
                    "binary blob); re-encode it as UTF-8, then re-run"
                    % _personal_path_mask_rel(rel))
            text = blob.raw.decode("utf-8", errors="replace")
            try:
                body = personal_path_hit_lines(
                    text,
                    deadline=time.monotonic() + _PERSONAL_PATH_FILE_BUDGET_S)
            except PersonalPathUnreadable as exc:
                # The refusal has to say WHICH file. Raised from the line
                # loop it named a deadline and nothing else, and the CLI
                # printed `FATAL: cannot read in-scope file matching did
                # not finish ...` -- true, and useless among thousands of
                # scanned entries (mechanism lane, round 22). Masked, like
                # every other path this rule prints.
                raise PersonalPathUnreadable(
                    "%s: %s" % (_personal_path_mask_rel(rel), str(exc)))
            if body:
                lines += body
                # Hashed only for a file that HIT, and hashed from the
                # bytes that were matched: this digest is what a row
                # pins, so it must describe the content the scan saw,
                # not the content a second read would find.
                digest = hashlib.sha256(blob.raw).hexdigest()
                digest_lf = hashlib.sha256(
                    blob.raw.replace(b"\r\n", b"\n")).hexdigest()
        if lines:
            hits.append(
                PersonalPathHit(rel=rel, lines=lines, sha256=digest,
                                sha256_lf=digest_lf))
    missed = set(modes) - seen_rels
    extra = seen_rels - set(modes)
    if extra:
        # The walk yielded a path the index snapshot does not hold.
        # Symmetric to `missed`, and equally a sign that the two
        # enumerations disagree (pair-rail round 4, P2).
        raise PersonalPathUnreadable(
            "the walk yielded %d file(s) git does not have in the "
            "index; the scan is inconsistent and has no verdict"
            % len(extra))
    if missed:
        # `modes` came from `git ls-files -s` in THIS call, so it is the
        # authoritative SET of what the walk should have seen. Zero was
        # only the loudest case: a walk that stops early is unverified in
        # exactly the same way, and reports clean over the files it never
        # reached. Comparing SETS rather than counts closes the shape a
        # count cannot see -- one path yielded twice and another never
        # (pair-rail round 3, P1). The message counts; it names no path,
        # because a path can be the leak.
        if not seen_rels:
            _personal_path_assert_enumerable(walker.repo_root)
        raise PersonalPathUnreadable(
            "the walk saw %d distinct file(s) and MISSED %d of the %d "
            "git has in the index; an incomplete scan has no verdict"
            % (len(seen_rels), len(missed), len(modes)))
    hits.sort(key=lambda h: h.rel)
    return PersonalPathScan(hits=hits)


#: `<path> | sha256:<64 hex> | <reason>`. The path carries no space and no
#: `|`; the digest is over the bytes the scan matched; the reason is
#: everything after the second `|`, stripped, and must not be empty.
#:
#: THE DIGEST IS THE CURE for "a row waives the file FOREVER" (pair-rail
#: land round 1, P2). A row used to be a decision about a PATH, and a path
#: outlives the reading that justified waiving it: the frozen transcript a
#: human read once could grow a second leak years later and stay silent.
#: Pinned to content, the row is a decision about BYTES -- it expires the
#: moment those bytes change, which is exactly when a human should look
#: again. The recoverable failure is loud and cheap: the gate names the
#: file, `--emit-personal-path-rows` prints the new row, a human re-reads
#: and commits it.
#:
#: A v3-shaped two-field row does NOT match, and an unmatched row is
#: MALFORMED, not ignored -- so an allowlist carried over from the previous
#: version fails the gate loudly instead of waiving without a digest.
#: The reason is captured GREEDILY and the trailing `\s*$` is gone. They
#: were an overlapping pair -- a lazy capture that grows one character at a
#: time while `\s*$` retries behind it -- and over a run of whitespace that
#: is quadratic: one row whose reason held 64 000 interior spaces took
#: 16.687 s (mechanism lane, round 22; reproduced). Nothing is lost, because
#: the caller has already applied `line.strip()`: there is no trailing
#: whitespace left for `\s*$` to consume, so the two spellings accept the
#: same rows and capture the same fields. That equivalence is MEASURED as a
#: differential over the 242 shipped rows and a table of row shapes rather
#: than argued from the pattern.

__all__ = [
    name for name, value in globals().items()
    if ((name.startswith("_") and not name.startswith("__"))
        or name.startswith("PersonalPath") or name in (
            "in_personal_path_scope", "line_is_personal_path_hit",
            "personal_path_hit_lines", "scan_personal_paths",
        ))
]
